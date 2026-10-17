"""The Topic Planner graph: a catalog topic becomes keywords, entities and validated sources,
then waits for the owner's approval.

    draft_profile → discover → validate → propose → review (interrupt) → apply
                       ↑           ↓
                       more_sites ←  (fewer than MIN_FEEDS readable feeds, once)

One model call drafts the profile; a second asks for other sites, with the reasons the first
ones failed, only when too few feeds can be used. Everything else is code. Graph state holds
plain JSON (dicts and lists), so checkpoints never deserialize our own classes.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Protocol, TypedDict
from urllib.parse import urljoin

import structlog
from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from dailyainotes.db import planner as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.exclusions import is_excluded
from dailyainotes.domain.matching import match_share, nearest_share
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
- candidate_sites: 10 to 15 https home or section pages of specialist publishers,
  independent sites and official bodies' press releases that cover the topic in English and
  publish often. Many big news outlets block AI crawlers in robots.txt, which makes their
  stories unusable here, so prefer smaller and official sources.
- arxiv_query: an arXiv API search query, only if the topic is scientific research; else null.
  Name a category with its subcategory or a wildcard, as in cat:q-bio.* or cat:cs.CL.
- github_repos: up to 3 owner/repo names you know exist, only if the topic is software; else [].
- hackernews_query: a short Hacker News search, only if the topic is technology; else null."""

MORE_PROMPT = """You find news sources for one topic of an English-language notebook. The
pages listed were tried already: some were kept, the others could not be used, each with the
reason. Propose 10 to 15 other https home or section pages of specialist publishers,
independent sites and official bodies' press releases that cover the topic in English and
publish often. Do not repeat a page from the list or another page of the same publisher."""

# What a proposal keeps, at most.
MAX_FEEDS = 8
MAX_FEEDS_PER_SITE = 2
# Where sites that link no feed often serve one anyway (WordPress, Hugo, most others).
USUAL_FEED_PATHS = ["feed", "rss", "rss.xml", "feed.xml", "index.xml", "atom.xml"]
MAX_REPOS = 2
# A feed is relevant when this share of its recent items names a keyword or an entity, or
# when this share of them is closer to this topic than to any other. Exact phrases rarely
# appear in headlines of a broad topic (Xbox Wire matched 10% for video games); on the live
# feeds of 2026-10-16, closest-topic shares were 50-100% on topic and 0-30% off it.
MIN_MATCH_SHARE = 0.2
MIN_TOPIC_SHARE = 0.35
# A relevant feed is useful only when a model may read its pages: this many of its recent items
# go through the policy gate, and at least this share must not be link-only. Many publishers'
# robots.txt blocks AI crawlers, which leaves every story they report unusable (2026-10-13).
READABLE_SAMPLE = 4
MIN_READABLE_SHARE = 0.5
RECENT = timedelta(days=30)
# With fewer readable feeds than this, the model is asked once more for other sites.
MIN_FEEDS = 3
ROUNDS = 2
MAX_SITES = 16


class ProfileDraft(BaseModel):
    keywords: list[str] = Field(min_length=3, max_length=20)
    negative_keywords: list[str] = Field(default_factory=list, max_length=10)
    entities: list[str] = Field(default_factory=list, max_length=20)
    candidate_sites: list[str] = Field(default_factory=list, max_length=MAX_SITES)
    arxiv_query: str | None = None
    github_repos: list[str] = Field(default_factory=list, max_length=3)
    hackernews_query: str | None = None


class MoreSites(BaseModel):
    candidate_sites: list[str] = Field(default_factory=list, max_length=MAX_SITES)


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
    # The round of site discovery (1 or 2) and the sites it tries.
    round: int
    sites: list[str]
    candidates: list[dict[str, Any]]
    # Every candidate checked in any round, and the sites that gave no feed, with the reason.
    checked: list[dict[str, Any]]
    dropped_sites: list[dict[str, str]]
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
    # None when the graph only resumes with the editor's decision, which embeds nothing.
    embeddings: Embeddings | None = None


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
        return {"draft": draft.model_dump(), "round": 1, "sites": draft.candidate_sites}

    async def discover(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        feeds, dropped_sites = await site_feeds(deps.http, fetcher, state["sites"])
        # Query sources come from the first draft; a later round only looks for sites.
        queries = query_sources(draft) if state["round"] == 1 else []
        seen = {c["locator"] for c in state.get("checked", [])}
        # A site may advertise a feed on another domain.
        candidates = [
            c
            for c in feeds + queries
            if not is_excluded(c["publisher_domain"]) and c["locator"] not in seen
        ]
        return {
            "candidates": candidates,
            "dropped_sites": state.get("dropped_sites", []) + dropped_sites,
        }

    async def validate(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        terms = draft.keywords + draft.entities
        embeddings = deps.embeddings
        if embeddings is None:
            raise RuntimeError("planning needs embeddings; only resuming a decision does not")
        texts = await db.topic_texts(deps.engine)
        ids = list(texts)
        topics = [await embeddings.aembed_query(texts[i]) for i in ids]

        async def closest(items: list[str]) -> float:
            vectors = await embeddings.aembed_documents(items)
            return nearest_share(vectors, topics, ids.index(state["topic_id"]))

        # With no other topic, every headline is closest to this one: keywords alone decide.
        compare = closest if len(ids) > 1 else None
        checked = state.get("checked", []) + [
            await check(deps.http, fetcher, candidate, terms, deps.now, compare)
            for candidate in state["candidates"]
        ]
        return {"checked": checked, "sources": keep(checked)}

    def enough(state: PlannerState) -> str:
        feeds = [s for s in state["sources"] if s["type"] == "rss"]
        return "propose" if len(feeds) >= MIN_FEEDS or state["round"] >= ROUNDS else "more_sites"

    async def more_sites(state: PlannerState) -> PlannerState:
        kept = [f"- {s['locator']}: kept" for s in state["sources"]]
        failed = [f"- {d['locator']}: {d['reason']}" for d in dropped(state)]
        found = await deps.router.structured(
            "planner",
            MoreSites,
            system=MORE_PROMPT,
            user=f"Topic: {state['name']}\nWhat it covers: {state['description']}\n"
            "Tried:\n" + "\n".join(kept + failed),
            run_id=state.get("run_id"),
        )
        tried = set(state["sites"]) | {d["locator"] for d in state.get("dropped_sites", [])}
        sites = [s for s in found.candidate_sites if s not in tried]
        return {"round": state["round"] + 1, "sites": sites}

    async def propose(state: PlannerState) -> PlannerState:
        draft = ProfileDraft.model_validate(state["draft"])
        profile = {
            "keywords": draft.keywords,
            "negative_keywords": draft.negative_keywords,
            "entities": draft.entities,
            "sources": state["sources"],
            # For the editor: what was tried and could not be used, and why.
            "dropped": dropped(state),
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
    for node in (draft_profile, discover, validate, more_sites, propose, review, apply):
        graph.add_node(node)
    graph.add_edge(START, "draft_profile")
    graph.add_edge("draft_profile", "discover")
    graph.add_edge("discover", "validate")
    graph.add_conditional_edges("validate", enough, ["more_sites", "propose"])
    graph.add_edge("more_sites", "discover")
    graph.add_edge("propose", "review")
    graph.add_edge("review", "apply")
    graph.add_edge("apply", END)
    return graph.compile(checkpointer=checkpointer)


async def site_feeds(
    http: Http, fetcher: ArticleFetcher, sites: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Feeds each site advertises, found by reading its `<link rel="alternate">` tags, and the
    sites that gave none, each with the reason."""
    found: list[dict[str, Any]] = []
    dropped_sites: list[dict[str, str]] = []
    for site in dict.fromkeys(sites):
        feeds, reason = await one_site(http, fetcher, site)
        found += [feed_source(url) for url in feeds]
        if not feeds:
            dropped_sites.append({"locator": site, "reason": reason})
    return found, dropped_sites


async def one_site(http: Http, fetcher: ArticleFetcher, site: str) -> tuple[list[str], str]:
    """The feeds one site offers, or why it gave none. A guessed address often fails where the
    site's home page links a feed, or a usual feed path serves one (found 2026-10-16: 11 of 27
    addresses the model gave for video games answered 404)."""
    if not site.startswith("https://"):
        return [], "not an https address"
    if is_excluded(registrable_domain(site)):
        return [], "an excluded publisher"
    feeds, reason = await linked_feeds(http, fetcher, site)
    if feeds or reason == "its robots.txt disallows us":
        return feeds, reason
    home = urljoin(site, "/")
    if home != site:
        feeds, _ = await linked_feeds(http, fetcher, home)
        if feeds:
            return feeds, ""
    for path in USUAL_FEED_PATHS:
        if await serves_feed(http, fetcher, urljoin(home, path)):
            return [urljoin(home, path)], ""
    return [], f"{reason}, nor serves one at the usual paths"


async def linked_feeds(http: Http, fetcher: ArticleFetcher, page: str) -> tuple[list[str], str]:
    """The page itself when it is a feed, or the feeds it links; else why not."""
    if not (await fetcher.robots(page)).allows(page):
        return [], "its robots.txt disallows us"
    try:
        response = await http.get(page)
    except Exception as error:
        log.info("site_unreachable", site=page, error=type(error).__name__)
        return [], f"unreachable ({type(error).__name__})"
    if response.status_code != 200:
        return [], f"answered {response.status_code}"
    if is_feed(response.content):
        return [page], ""
    feeds = discover_feeds(response.text, str(response.url))[:MAX_FEEDS_PER_SITE]
    return feeds, "" if feeds else "advertises no feed"


async def serves_feed(http: Http, fetcher: ArticleFetcher, url: str) -> bool:
    if not (await fetcher.robots(url)).allows(url):
        return False
    try:
        response = await http.get(url)
    except Exception:
        return False
    return response.status_code == 200 and is_feed(response.content)


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
    http: Http,
    fetcher: ArticleFetcher,
    candidate: dict[str, Any],
    terms: list[str],
    now: datetime,
    closest: Callable[[list[str]], Awaitable[float]] | None,
) -> dict[str, Any]:
    """Fetch a candidate once: how many recent items it has, how many name the topic or are
    closest to it, and, for a relevant feed, how many of its pages a model may read."""
    spec = SourceSpec(candidate["type"], candidate["locator"], candidate["config"])
    try:
        outcome = await fetch_source(http, spec, now=now)
    except Exception as error:
        return {**candidate, "recent_items": 0, "match_share": 0.0, "note": type(error).__name__}
    recent = [i for i in outcome.items if i.published_at is None or now - i.published_at <= RECENT]
    texts = [f"{i.title} {i.lead}" for i in recent[:20]]
    checked = {
        **candidate,
        "recent_items": len(recent),
        "match_share": round(match_share(texts, terms), 2),
        "note": "",
    }
    if candidate["type"] == "rss" and closest is not None:
        checked["topic_share"] = round(await closest(texts), 2) if texts else 0.0
    if candidate["type"] == "rss" and recent and on_topic(checked):
        try:
            sample = [await fetcher.decide(i.url) for i in recent[:READABLE_SAMPLE]]
        except Exception as error:
            # One odd page must not stop the plan; the feed counts as unreadable.
            note = f"its pages could not be checked ({type(error).__name__})"
            return {**checked, "readable_share": 0.0, "note": note}
        readable = sum(d.text_policy != "link_only" for d in sample) / len(sample)
        checked["readable_share"] = round(readable, 2)
        if readable < MIN_READABLE_SHARE:
            checked["note"] = next(d.reason for d in sample if d.text_policy == "link_only")
    return checked


def keep(checked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sources with recent items; feeds must also be on topic, with pages a model may read.
    Best matches first."""
    feeds = sorted(
        (
            c
            for c in checked
            if c["type"] == "rss"
            and c["recent_items"]
            and on_topic(c)
            and c.get("readable_share", 0.0) >= MIN_READABLE_SHARE
        ),
        key=lambda c: (-max(c["match_share"], c.get("topic_share", 0.0)), -c["recent_items"]),
    )
    # Query sources (arXiv, GitHub, HN) are on topic by construction.
    others = [c for c in checked if c["type"] != "rss" and c["recent_items"]]
    return feeds[:MAX_FEEDS] + others


def on_topic(checked: dict[str, Any]) -> bool:
    keywords: float = checked["match_share"]
    closest: float = checked.get("topic_share", 0.0)
    return keywords >= MIN_MATCH_SHARE or closest >= MIN_TOPIC_SHARE


def dropped(state: PlannerState) -> list[dict[str, str]]:
    """Everything tried that the plan does not keep, with the reason."""
    kept = {s["locator"] for s in state.get("sources", [])}
    return state.get("dropped_sites", []) + [
        {"locator": c["locator"], "reason": drop_reason(c)}
        for c in state.get("checked", [])
        if c["locator"] not in kept
    ]


def drop_reason(candidate: dict[str, Any]) -> str:
    if not candidate["recent_items"]:
        note = candidate["note"]
        return f"could not be read ({note})" if note else "nothing in the last 30 days"
    if candidate["type"] == "rss" and not on_topic(candidate):
        share = candidate.get("topic_share", 0.0)
        return f"off topic: {share:.0%} of recent items are closest to this topic"
    if candidate["type"] == "rss" and candidate.get("readable_share", 0.0) < MIN_READABLE_SHARE:
        return f"its pages are link-only: {candidate['note']}"
    return "more readable feeds were kept"
