"""Ingest a topic: fetch each of its sources, decide what each new item's text may be used
for, and save it with its chunks and their embeddings."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import structlog
from langchain_core.embeddings import Embeddings

from dailyainotes.db import ingest as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.chunking import chunk_text, heading_chunk
from dailyainotes.domain.exclusions import is_excluded
from dailyainotes.sources.connectors import SourceSpec, fetch_source
from dailyainotes.sources.fetcher import ArticleFetcher, PageDecision
from dailyainotes.sources.http import Http
from dailyainotes.sources.items import RawItem
from dailyainotes.sources.urls import canonical_url, registrable_domain, url_hash

log = structlog.get_logger(__name__)

# Feeds can carry years of items (one carries its whole history); only recent ones matter.
MAX_ITEM_AGE = timedelta(days=7)
MAX_NEW_ITEMS_PER_SOURCE = 20
# INTENT.md, Architectural Constraints: source text is purged after 30 days.
CONTENT_RETENTION = timedelta(days=30)
# These connectors return the publisher's own text (an abstract, release notes); their pages
# are not fetched.
API_TEXT_SOURCES = {"arxiv", "github_releases"}


@dataclass(frozen=True)
class SavedDocument:
    title: str
    url: str
    text_policy: str
    reason: str


@dataclass
class SourceReport:
    type: str
    locator: str
    fetched: int = 0
    saved: list[SavedDocument] = field(default_factory=list)
    not_modified: bool = False
    error: str | None = None


async def ingest_topic(
    *,
    engine: AsyncEngine,
    http: Http,
    embeddings: Embeddings,
    slug: str,
    now: datetime,
    github_token: str | None = None,
) -> list[SourceReport]:
    fetcher = ArticleFetcher(http)
    reports = []
    for source in await db.sources_for_topic(engine, slug):
        report = SourceReport(source.type, source.locator)
        reports.append(report)
        if source.type == "rss" and is_excluded(registrable_domain(source.locator)):
            # A plan approved before the check existed may have added one (INTENT.md).
            report.error = "excluded publisher"
            log.warning("source_skipped", source=source.locator, reason=report.error)
            continue
        spec = SourceSpec(
            source.type, source.locator, source.config, source.etag, source.last_modified
        )
        try:
            outcome = await fetch_source(http, spec, now=now, github_token=github_token)
        except Exception as error:
            # One failing source must not stop the others; the streak shows up in the data.
            report.error = f"{type(error).__name__}: {error}"
            await db.record_failure(engine, source.id, at=now)
            log.warning("source_failed", source=source.locator, error=report.error)
            continue
        await db.record_fetch(
            engine, source.id, etag=outcome.etag, last_modified=outcome.last_modified, at=now
        )
        report.fetched, report.not_modified = len(outcome.items), outcome.not_modified
        for item in await new_items(engine, outcome.items, now=now):
            saved = await save_item(engine, fetcher, embeddings, source, item, now=now)
            if saved:
                report.saved.append(saved)
        log.info(
            "source_fetched", source=source.locator, items=report.fetched, saved=len(report.saved)
        )
    return reports


async def new_items(engine: AsyncEngine, items: list[RawItem], *, now: datetime) -> list[RawItem]:
    recent = [i for i in items if i.published_at is None or now - i.published_at <= MAX_ITEM_AGE]
    known = await db.known_hashes(engine, [url_hash(i.url) for i in recent])
    unseen = {url_hash(i.url): i for i in recent if url_hash(i.url) not in known}
    return list(unseen.values())[:MAX_NEW_ITEMS_PER_SOURCE]


async def save_item(
    engine: AsyncEngine,
    fetcher: ArticleFetcher,
    embeddings: Embeddings,
    source: db.SourceRecord,
    item: RawItem,
    *,
    now: datetime,
) -> SavedDocument | None:
    if source.type in API_TEXT_SOURCES:
        publisher_id = source.publisher_id
        decision = PageDecision("summary", "the publisher's text from its API")
    else:
        publisher = await db.publisher_for(engine, registrable_domain(item.url))
        publisher_id = publisher.id
        decision = await fetcher.decide(item.url, publisher_paywalled=publisher.paywalled)
    texts = [heading_chunk(item.title, item.lead)]
    if decision.content:
        texts += chunk_text(decision.content)
    vectors = await embeddings.aembed_documents(texts)
    document_id = await db.save_document(
        engine,
        db.NewDocument(
            # Without tracking parameters: this is the link readers will see.
            url=canonical_url(item.url),
            canonical_url_hash=url_hash(item.url),
            source_id=source.id,
            publisher_id=publisher_id,
            title=item.title,
            lead=item.lead,
            published_at=item.published_at,
            text_policy=decision.text_policy,
            policy_reason=decision.reason,
            content=decision.content,
            content_purge_after=now + CONTENT_RETENTION if decision.content else None,
        ),
        list(zip(texts, vectors, strict=True)),
    )
    if document_id is None:
        return None
    return SavedDocument(item.title, canonical_url(item.url), decision.text_policy, decision.reason)
