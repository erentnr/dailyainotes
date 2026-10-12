"""The topic catalog in `config/catalog.toml`, validated and loaded into the database."""

import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from dailyainotes.db import catalog as catalog_db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.exclusions import is_excluded
from dailyainotes.domain.trust import TRUST_PRIOR, PublisherKind
from dailyainotes.sources.urls import registrable_domain

CATALOG_PATH = Path("config/catalog.toml")


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")


def allowed(domain_or_url: str) -> str:
    """Refuse a publisher INTENT.md excludes."""
    if is_excluded(registrable_domain(domain_or_url)):
        raise ValueError(f"{domain_or_url} belongs to an excluded publisher (INTENT.md)")
    return domain_or_url


Allowed = AfterValidator(allowed)


class PublisherEntry(Entry):
    domain: Annotated[str, Allowed]
    name: str
    kind: PublisherKind
    owner_group: str | None = None


class RssSource(Entry):
    type: Literal["rss"]
    url: Annotated[str, Field(pattern=r"^https://"), Allowed]
    # The publisher when the feed's domain is not the articles' domain.
    publisher: Annotated[str, Allowed] | None = None


class ArxivSource(Entry):
    type: Literal["arxiv"]
    query: str


class GitHubReleasesSource(Entry):
    type: Literal["github_releases"]
    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")


class HackerNewsSource(Entry):
    type: Literal["hackernews"]
    query: str
    min_points: int = 50


SourceEntry = Annotated[
    RssSource | ArxivSource | GitHubReleasesSource | HackerNewsSource, Field(discriminator="type")
]


class TopicEntry(Entry):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    name: str
    description: str
    controversial: bool = False
    sources: list[SourceEntry] = []


class Catalog(Entry):
    publishers: list[PublisherEntry] = []
    topics: list[TopicEntry]


def locator(source: SourceEntry) -> str:
    match source:
        case RssSource():
            return source.url
        case ArxivSource() | HackerNewsSource():
            return source.query
        case GitHubReleasesSource():
            return source.repo


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    with path.open("rb") as file:
        return Catalog.model_validate(tomllib.load(file))


async def sync_catalog(engine: AsyncEngine, catalog: Catalog) -> catalog_db.SyncCounts:
    publishers = [
        catalog_db.PublisherRow(
            domain=p.domain,
            name=p.name,
            kind=p.kind,
            owner_group=p.owner_group or p.domain,
            trust_prior=TRUST_PRIOR[p.kind],
        )
        for p in catalog.publishers
    ]
    topics = [
        catalog_db.TopicRow(
            slug=t.slug,
            name=t.name,
            description=t.description,
            controversial=t.controversial,
            sources=[
                catalog_db.SourceRow(
                    type=s.type,
                    locator=locator(s),
                    config=s.model_dump(exclude_none=True),
                    publisher_domain=publisher_domain(s),
                )
                for s in t.sources
            ],
        )
        for t in catalog.topics
    ]
    return await catalog_db.sync(engine, publishers, topics)


def publisher_domain(source: SourceEntry) -> str | None:
    """The publisher a source's own items come from; None for aggregators like HN."""
    match source:
        case RssSource():
            return source.publisher or registrable_domain(source.url)
        case ArxivSource():
            return "arxiv.org"
        case GitHubReleasesSource():
            return f"github.com/{source.repo.split('/')[0]}"
        case HackerNewsSource():
            return None
