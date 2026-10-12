"""Scout, the edition graph for one topic and day: collect → cluster → rank.

All code, no model: ingestion fetches new items, clustering groups the recent ones into
stories, ranking scores them and picks the few worth a note. Every story is saved, picked or
not, with its reasons, so the ranking can be audited. Each picked story then gets its own
story graph (graphs/story.py).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, TypedDict

from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from dailyainotes.db import editorial as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.clustering import Item, cluster
from dailyainotes.domain.editorial import Report, rank_story
from dailyainotes.ingestion.run import ingest_topic
from dailyainotes.sources.http import Http

# Documents published (or, when undated, fetched) this recently are candidates.
WINDOW = timedelta(hours=36)


class ScoutState(TypedDict, total=False):
    topic_id: int
    slug: str
    edition_id: int
    # How many stories may be picked; the edition runner sets it.
    cap: int
    collected: int
    # Candidates without their vectors, keyed by document id as a string (JSON keys).
    candidates: dict[str, dict[str, Any]]
    groups: list[list[int]]
    stories: int
    picked: list[int]


@dataclass(frozen=True)
class ScoutDeps:
    engine: AsyncEngine
    http: Http
    embeddings: Embeddings
    now: datetime
    collect: bool = True
    github_token: str | None = None


def build_scout(
    deps: ScoutDeps, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[ScoutState, None, ScoutState, ScoutState]:
    async def collect(state: ScoutState) -> ScoutState:
        if not deps.collect:
            return {"collected": 0}
        reports = await ingest_topic(
            engine=deps.engine,
            http=deps.http,
            embeddings=deps.embeddings,
            slug=state["slug"],
            now=deps.now,
            github_token=deps.github_token,
        )
        return {"collected": sum(len(r.saved) for r in reports)}

    async def group(state: ScoutState) -> ScoutState:
        documents = await db.candidate_documents(deps.engine, state["topic_id"], deps.now - WINDOW)
        candidates = {
            str(d.id): {
                "title": d.title,
                "published_at": d.published_at.isoformat() if d.published_at else None,
                "text_policy": d.text_policy,
                "owner_group": d.owner_group,
                "trust": d.trust,
            }
            for d in documents
        }
        groups = cluster([Item(d.id, d.vector, d.published_at) for d in documents])
        return {"candidates": candidates, "groups": groups}

    async def rank(state: ScoutState) -> ScoutState:
        ranked = []
        for ids in state["groups"]:
            members = [state["candidates"][str(i)] for i in ids]
            reports = [
                Report(
                    m["owner_group"],
                    m["trust"],
                    datetime.fromisoformat(m["published_at"]) if m["published_at"] else None,
                )
                for m in members
            ]
            texts = [m for m in members if m["text_policy"] != "link_only"]
            headline = max(texts or members, key=lambda m: m["trust"])["title"]
            ranked.append((rank_story(reports, deps.now), ids, headline, bool(texts)))
        ranked.sort(key=lambda r: -r[0].score)
        stories: list[db.NewStory] = []
        picked = 0
        for score, ids, headline, readable in ranked:
            # A story only link-only publishers covered has no text a model may read.
            pick = readable and picked < state["cap"]
            picked += pick
            reasons = score.reasons + ([] if readable else ["only link-only reports"])
            stories.append(
                db.NewStory(headline, ids, score.independent, score.score, reasons, pick)
            )
        picked_ids = await db.save_stories(deps.engine, state["edition_id"], stories)
        return {"stories": len(stories), "picked": picked_ids}

    graph = StateGraph(ScoutState)
    graph.add_sequence([collect, group, rank])
    graph.add_edge(START, "collect")
    graph.add_edge("rank", END)
    return graph.compile(checkpointer=checkpointer)
