"""The Topic Planner graph: a catalog topic becomes keywords, entities and validated sources,
then waits for the owner's approval.

    draft_profile → discover → validate → propose → review (interrupt) → apply

One model call drafts the profile; everything else is code. Graph state holds plain JSON
(dicts and lists), so checkpoints never deserialize our own classes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol, TypedDict

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from dailyainotes.db import planner as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.exclusions import is_excluded
from dailyainotes.domain.matching import match_share
from dailyainotes.sources.connectors import SourceSpec, fetch_source
from dailyainotes.sources.fetcher import ArticleFetcher
from dailyainotes.sources.http import Http
from dailyainotes.sources.rss import discover_feeds, is_feed
from dailyainotes.sources.urls import registrable_domain

log = structlog.get_logger(__name__)

PROMPT = """You plan daily news coverage of one topic for an English-language notebook.
Propose:
- keywords: 5 to 15 lower-case words or phrases that headlines about this topic use.
- negative_keywords: up to 10 phrases that mean a different subject with similar words.
- entities: up to 15 names of the people, teams, organisations and products at its centre.
- candidate_sites: 5 to 10 https home pages or section pages of established publishers,
  official bodies and specialist sites that cover the topic in English and publish often.
- arxiv_query: an arXiv API search query, only if the topic is scientific research; else null.
- github_repos: up to 3 owner/repo names, only if the topic is software; else [].
- hackernews_query: a short Hacker News search, only if the topic is technology; else null."""

# What a proposal keeps, at most.
MAX_FEEDS = 8
MAX_FEEDS_PER_SITE = 2
MAX_REPOS = 2
# A feed is relevant when this share of its recent items names a keyword or an entity.
MIN_MATCH_SHARE = 0.2
RECENT = timedelta(days=30)


class ProfileDraft(BaseModel):
    keywords: list[str] = Field(min_length=3, max_length=20)
    negative_keywords: list[str] = Field(default_factory=list, max_length=10)
    entities: list[str] = Field(default_factory=list, max_length=20)
    candidate_sites: list[str] = Field(default_factory=list, max_length=12)
    arxiv_query: str | None = None
    github_repos: list[str] = Field(default_factory=list, max_length=3)
    hackernews_query: str | None = None


class Decision(TypedDict):
    decision: Literal["approve", "reject"]
    # Who decided: the editor's email from /admin, or "dan review".
    by: str
    comment: str


class PlannerState(TypedDict, total=False):
    topic_id: int
    slug: str
    name: str
    description: str
    version: int
    thread_id: str
    run_id: int
    draft: dict[str, Any]
    candidates: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    proposal_id: int
    decision: Decision


class StructuredModel(Protocol):
    async def structured[T: BaseModel](
        self, role: str, schema: type[T], *, system: str, user: str, run_id: int | None = None
    ) -> T: ...


@dataclass(frozen=True)
class PlannerDeps:
    engine: AsyncEngine
    router: StructuredModel
    http: Http
    now: datetime


def build_planner(
    deps: PlannerDeps, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[PlannerState, None, PlannerState, PlannerState]:
    fetcher = ArticleFetcher(deps.http)

    async def draft_profile(state: PlannerState) -> PlannerState:
        draft = await deps.router.structured(
            "planner",
            ProfileDraft,
            system=PROMPT,
            user=f"Topic: {state['name']}\nWhat it covers: {state['description']}",
            run_id=state.get("run_id"),
        )
        return {"draft": draft.model_dump()}

    async def discover(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        feeds = await site_feeds(deps.http, fetcher, draft.candidate_sites)
        # A site may advertise a feed on another domain.
        candidates = [
            c for c in feeds + query_sources(draft) if not is_excluded(c["publisher_domain"])
        ]
        return {"candidates": candidates}

    async def validate(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        terms = draft.keywords + draft.entities
        checked = [
            await check(deps.http, candidate, terms, deps.now) for candidate in state["candidates"]
        ]
        return {"sources": keep(checked)}

    async def propose(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        profile = {
            "keywords": draft.keywords,
            "negative_keywords": draft.negative_keywords,
            "entities": draft.entities,
            "sources": state["sources"],
        }
        proposal_id = await db.save_proposal(
            deps.engine, state["topic_id"], state["version"], profile, state["thread_id"]
        )
        return {"proposal_id": proposal_id}

    def review(state: PlannerState) -> PlannerState:
        # Pauses the graph; `dan review approve|reject` resumes it with the decision.
        decision: Decision = interrupt({"proposal_id": state["proposal_id"], "slug": state["slug"]})
        return {"decision": decision}

    async def apply(state: PlannerState) -> PlannerState:
        decision = state["decision"]
        if decision["decision"] == "approve":
            await db.approve(deps.engine, state["proposal_id"], decision["comment"], decision["by"])
        else:
            await db.reject(deps.engine, state["proposal_id"], decision["comment"], decision["by"])
        return {}

    graph = StateGraph(PlannerState)
    graph.add_sequence([draft_profile, discover, validate, propose, review, apply])
    graph.add_edge(START, "draft_profile")
    graph.add_edge("apply", END)
    return graph.compile(checkpointer=checkpointer)


async def site_feeds(http: Http, fetcher: ArticleFetcher, sites: list[str]) -> list[dict[str, Any]]:
    """Feeds each site advertises, found by reading its `<link rel="alternate">` tags."""
    found: list[dict[str, Any]] = []
    for site in dict.fromkeys(s for s in sites if s.startswith("https://")):
        if is_excluded(registrable_domain(site)):
            continue
        robots = await fetcher.robots(site)
        if not robots.allows(site):
            continue
        try:
            response = await http.get(site)
        except Exception as error:
            log.info("site_unreachable", site=site, error=type(error).__name__)
            continue
        if response.status_code != 200:
            continue
        if is_feed(response.content):
            feeds = [site]
        else:
            feeds = discover_feeds(response.text, str(response.url))[:MAX_FEEDS_PER_SITE]
        found += [feed_source(url) for url in feeds]
    return found


def feed_source(url: str) -> dict[str, Any]:
    return {
        "type": "rss",
        "locator": url,
        "config": {"type": "rss", "url": url},
        "publisher_domain": registrable_domain(url),
    }


def query_sources(draft: ProfileDraft) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    if draft.arxiv_query:
        sources.append(
            {
                "type": "arxiv",
                "locator": draft.arxiv_query,
                "config": {"type": "arxiv", "query": draft.arxiv_query},
                "publisher_domain": "arxiv.org",
            }
        )
    for repo in draft.github_repos[:MAX_REPOS]:
        sources.append(
            {
                "type": "github_releases",
                "locator": repo,
                "config": {"type": "github_releases", "repo": repo},
                "publisher_domain": f"github.com/{repo.split('/')[0]}",
            }
        )
    if draft.hackernews_query:
        sources.append(
            {
                "type": "hackernews",
                "locator": draft.hackernews_query,
                "config": {
                    "type": "hackernews",
                    "query": draft.hackernews_query,
                    "min_points": 50,
                },
                "publisher_domain": None,
            }
        )
    return sources


async def check(
    http: Http, candidate: dict[str, Any], terms: list[str], now: datetime
) -> dict[str, Any]:
    """Fetch a candidate once: how many recent items it has, and how many name the topic."""
    spec = SourceSpec(candidate["type"], candidate["locator"], candidate["config"])
    try:
        outcome = await fetch_source(http, spec, now=now)
    except Exception as error:
        return {**candidate, "recent_items": 0, "match_share": 0.0, "note": type(error).__name__}
    recent = [i for i in outcome.items if i.published_at is None or now - i.published_at <= RECENT]
    share = match_share([f"{i.title} {i.lead}" for i in recent[:20]], terms)
    return {**candidate, "recent_items": len(recent), "match_share": round(share, 2), "note": ""}


def keep(checked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sources with recent items; feeds must also be on topic. Best matches first."""
    feeds = sorted(
        (
            c
            for c in checked
            if c["type"] == "rss" and c["recent_items"] and c["match_share"] >= MIN_MATCH_SHARE
        ),
        key=lambda c: (-c["match_share"], -c["recent_items"]),
    )
    # Query sources (arXiv, GitHub, HN) are on topic by construction.
    others = [c for c in checked if c["type"] != "rss" and c["recent_items"]]
    return feeds[:MAX_FEEDS] + others
