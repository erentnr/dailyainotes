"""What Scout and the story graph read and write: editions, stories, notes, their versions,
citations, claims and approvals."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, delete, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, insert

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import (
    Approval,
    Chunk,
    Citation,
    Claim,
    ClaimCheck,
    Document,
    Edition,
    Note,
    NoteVersion,
    Publisher,
    Source,
    Story,
    StoryDocument,
    Topic,
    TopicSource,
)

# How much of each document the story graph gets: its heading and first text chunks.
EVIDENCE_CHUNKS = 3


@dataclass(frozen=True)
class CandidateDocument:
    id: int
    title: str
    published_at: datetime | None
    text_policy: str
    owner_group: str
    trust: float
    vector: list[float]


@dataclass(frozen=True)
class NewStory:
    title: str
    document_ids: list[int]
    independent_publishers: int
    score: float
    reasons: list[str]
    picked: bool


@dataclass(frozen=True)
class EvidenceDocument:
    document_id: int
    title: str
    url: str
    publisher: str
    kind: str
    owner_group: str
    trust: float
    published_at: datetime | None
    text: str


@dataclass(frozen=True)
class CitationRow:
    marker: int
    document_id: int
    url: str
    title: str
    publisher: str
    published_at: datetime | None
    quote: str


@dataclass(frozen=True)
class ClaimRow:
    text: str
    kind: str
    markers: list[int]
    verdict: str
    independent_origins: int
    supporting_markers: list[int]
    rationale: str


@dataclass(frozen=True)
class VersionText:
    title: str
    body: str
    why_it_matters: str


@dataclass(frozen=True)
class NoteSummary:
    id: int
    slug: str
    topic: str
    status: str
    edition_date: date
    thread_id: str
    title: str
    version: int
    supported: int
    claims: int


async def start_edition(engine: AsyncEngine, topic_id: int, day: date) -> tuple[int, str]:
    """The day's edition for a topic, created if new; its id and status."""
    async with engine.begin() as connection:
        await connection.execute(
            insert(Edition).values(topic_id=topic_id, date=day).on_conflict_do_nothing()
        )
        edition_id, status = (
            await connection.execute(
                select(Edition.id, Edition.status).where(
                    Edition.topic_id == topic_id, Edition.date == day
                )
            )
        ).one()
    return edition_id, status


async def finish_edition(
    engine: AsyncEngine, edition_id: int, status: str, stats: dict[str, Any]
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(Edition)
            .where(Edition.id == edition_id)
            .values(status=status, stats=stats, finished_at=func.now())
        )


async def candidate_documents(
    engine: AsyncEngine, topic_id: int, since: datetime
) -> list[CandidateDocument]:
    """Recent documents of the topic's sources not yet in any story, with their heading vector."""
    in_topic = select(TopicSource.source_id).where(TopicSource.topic_id == topic_id)
    in_a_story = select(StoryDocument.document_id)
    statement = (
        select(
            Document.id,
            Document.title,
            Document.published_at,
            Document.text_policy,
            func.coalesce(Publisher.owner_group, Source.locator),
            func.coalesce(Publisher.trust_prior, 0.5),
            Chunk.embedding,
        )
        .join(Chunk, and_(Chunk.document_id == Document.id, Chunk.ordinal == 0))
        .join(Source, Source.id == Document.source_id)
        .outerjoin(Publisher, Publisher.id == Document.publisher_id)
        .where(
            Document.source_id.in_(in_topic),
            Document.id.not_in(in_a_story),
            or_(
                Document.published_at >= since,
                and_(Document.published_at.is_(None), Document.fetched_at >= since),
            ),
        )
    )
    async with engine.connect() as connection:
        rows = await connection.execute(statement)
        return [CandidateDocument(r[0], r[1], r[2], r[3], r[4], r[5], list(r[6])) for r in rows]


async def save_stories(engine: AsyncEngine, edition_id: int, stories: list[NewStory]) -> list[int]:
    """Every story of the edition, picked or not, so the ranking can be audited; returns the
    ids of the picked ones, best first."""
    picked: list[int] = []
    async with engine.begin() as connection:
        for story in stories:
            story_id = (
                await connection.execute(
                    insert(Story)
                    .values(
                        edition_id=edition_id,
                        title=story.title,
                        document_count=len(story.document_ids),
                        independent_publishers=story.independent_publishers,
                        score=story.score,
                        reasons=story.reasons,
                        picked=story.picked,
                    )
                    .returning(Story.id)
                )
            ).scalar_one()
            if story.document_ids:
                await connection.execute(
                    insert(StoryDocument),
                    [{"story_id": story_id, "document_id": d} for d in story.document_ids],
                )
            if story.picked:
                picked.append(story_id)
    return picked


async def picked_stories(engine: AsyncEngine, edition_id: int) -> list[int]:
    """The edition's picked stories, best first; empty until Scout has ranked it."""
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(Story.id)
            .where(Story.edition_id == edition_id, Story.picked)
            .order_by(Story.score.desc(), Story.id)
        )
        return list(rows.scalars())


async def picked_on(engine: AsyncEngine, day: date) -> int:
    """Stories picked across all of the day's editions, for the daily cap."""
    async with engine.connect() as connection:
        count: int = (
            await connection.execute(
                select(func.count())
                .select_from(Story)
                .join(Edition, Edition.id == Story.edition_id)
                .where(Edition.date == day, Story.picked)
            )
        ).scalar_one()
    return count


async def note_for_id(engine: AsyncEngine, note_id: int) -> tuple[str, str] | None:
    """The note's status and thread id."""
    async with engine.connect() as connection:
        row = (
            await connection.execute(select(Note.status, Note.thread_id).where(Note.id == note_id))
        ).one_or_none()
    return (row[0], row[1]) if row else None


async def note_for_story(engine: AsyncEngine, story_id: int) -> tuple[int, str] | None:
    """The story's note id and status, if it has a note."""
    async with engine.connect() as connection:
        row = (
            await connection.execute(select(Note.id, Note.status).where(Note.story_id == story_id))
        ).one_or_none()
    return (row[0], row[1]) if row else None


async def story_evidence(engine: AsyncEngine, story_id: int) -> list[EvidenceDocument]:
    """The story's documents a model may read: never link-only ones (INTENT.md, Copyright)."""
    statement = (
        select(
            Document.id,
            Document.title,
            Document.url,
            func.coalesce(Publisher.name, "Unknown publisher"),
            func.coalesce(Publisher.kind, "unknown"),
            func.coalesce(Publisher.owner_group, Document.url),
            func.coalesce(Publisher.trust_prior, 0.5),
            Document.published_at,
            func.string_agg(Chunk.text, aggregate_order_by(literal("\n\n"), Chunk.ordinal)),
        )
        .join(StoryDocument, StoryDocument.document_id == Document.id)
        .join(Chunk, and_(Chunk.document_id == Document.id, Chunk.ordinal < EVIDENCE_CHUNKS))
        .outerjoin(Publisher, Publisher.id == Document.publisher_id)
        .where(StoryDocument.story_id == story_id, Document.text_policy != "link_only")
        .group_by(Document.id, Publisher.id)
        .order_by(func.coalesce(Publisher.trust_prior, 0.5).desc(), Document.id)
    )
    async with engine.connect() as connection:
        return [EvidenceDocument(*row) for row in await connection.execute(statement)]


async def story_header(engine: AsyncEngine, story_id: int) -> tuple[int, str, date]:
    """The story's topic id, title and edition date."""
    async with engine.connect() as connection:
        topic_id, title, day = (
            await connection.execute(
                select(Edition.topic_id, Story.title, Edition.date)
                .join(Edition, Edition.id == Story.edition_id)
                .where(Story.id == story_id)
            )
        ).one()
    return topic_id, title, day


async def create_note(
    engine: AsyncEngine, story_id: int, topic_id: int, day: date, slug: str, thread_id: str
) -> int:
    """Idempotent per story: a rerun gets the same note."""
    async with engine.begin() as connection:
        taken = await connection.execute(
            select(Note.id).where(Note.slug == slug, Note.story_id != story_id)
        )
        if taken.first():
            # Two stories with one headline on the same day.
            slug = f"{slug}-{story_id}"
        await connection.execute(
            insert(Note)
            .values(
                story_id=story_id,
                topic_id=topic_id,
                edition_date=day,
                slug=slug,
                thread_id=thread_id,
            )
            .on_conflict_do_nothing(index_elements=["story_id"])
        )
        note_id: int = (
            await connection.execute(select(Note.id).where(Note.story_id == story_id))
        ).scalar_one()
    return note_id


async def save_version(
    engine: AsyncEngine,
    note_id: int,
    version: int,
    *,
    title: str,
    body: str,
    why_it_matters: str,
    citations: list[CitationRow],
) -> int:
    async with engine.begin() as connection:
        version_id: int = (
            await connection.execute(
                insert(NoteVersion)
                .values(
                    note_id=note_id,
                    version=version,
                    title=title,
                    body=body,
                    why_it_matters=why_it_matters,
                )
                .on_conflict_do_update(
                    index_elements=["note_id", "version"],
                    set_={"title": title, "body": body, "why_it_matters": why_it_matters},
                )
                .returning(NoteVersion.id)
            )
        ).scalar_one()
        # A retried node rewrites its version whole.
        await connection.execute(delete(Citation).where(Citation.note_version_id == version_id))
        if citations:
            await connection.execute(
                insert(Citation).values(
                    [{"note_version_id": version_id, **c.__dict__} for c in citations]
                )
            )
    return version_id


async def save_claims(engine: AsyncEngine, version_id: int, claims: list[ClaimRow]) -> None:
    async with engine.begin() as connection:
        # Checks go with their claims (ON DELETE CASCADE).
        await connection.execute(delete(Claim).where(Claim.note_version_id == version_id))
        for ordinal, claim in enumerate(claims):
            claim_id = (
                await connection.execute(
                    insert(Claim)
                    .values(
                        note_version_id=version_id,
                        ordinal=ordinal,
                        text=claim.text,
                        kind=claim.kind,
                        markers=claim.markers,
                    )
                    .returning(Claim.id)
                )
            ).scalar_one()
            await connection.execute(
                insert(ClaimCheck).values(
                    claim_id=claim_id,
                    verdict=claim.verdict,
                    independent_origins=claim.independent_origins,
                    supporting_markers=claim.supporting_markers,
                    rationale=claim.rationale,
                )
            )


async def set_status(engine: AsyncEngine, note_id: int, status: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(update(Note).where(Note.id == note_id).values(status=status))


async def decide(
    engine: AsyncEngine, note_id: int, version: int, decision: str, comment: str
) -> None:
    """Record the approval or rejection and publish or reject the note, in one transaction."""
    async with engine.begin() as connection:
        await connection.execute(
            insert(Approval).values(
                note_id=note_id, version=version, decision=decision, comment=comment
            )
        )
        values: dict[str, Any] = {"status": "rejected"}
        if decision == "approve":
            values = {
                "status": "published",
                "published_version": version,
                "published_at": func.now(),
            }
        await connection.execute(update(Note).where(Note.id == note_id).values(**values))


async def index_note(
    engine: AsyncEngine, note_id: int, search_text: str, embedding: list[float]
) -> None:
    """What Ask searches: the published text and its vector (the full-text index follows)."""
    async with engine.begin() as connection:
        await connection.execute(
            update(Note)
            .where(Note.id == note_id)
            .values(search_text=search_text, embedding=embedding)
        )


async def notes(engine: AsyncEngine, *, status: str | None = None) -> list[NoteSummary]:
    """Each note with its latest version and how many of its claims are supported."""
    latest = (
        select(NoteVersion.note_id, func.max(NoteVersion.version).label("version"))
        .group_by(NoteVersion.note_id)
        .subquery()
    )
    claims = (
        select(
            Claim.note_version_id,
            func.count().label("claims"),
            func.count().filter(ClaimCheck.verdict == "supported").label("supported"),
        )
        .join(ClaimCheck, ClaimCheck.claim_id == Claim.id)
        .group_by(Claim.note_version_id)
        .subquery()
    )
    statement = (
        select(
            Note.id,
            Note.slug,
            Topic.slug,
            Note.status,
            Note.edition_date,
            Note.thread_id,
            NoteVersion.title,
            NoteVersion.version,
            func.coalesce(claims.c.supported, 0),
            func.coalesce(claims.c.claims, 0),
        )
        .join(Topic, Topic.id == Note.topic_id)
        .join(latest, latest.c.note_id == Note.id)
        .join(
            NoteVersion,
            and_(NoteVersion.note_id == Note.id, NoteVersion.version == latest.c.version),
        )
        .outerjoin(claims, claims.c.note_version_id == NoteVersion.id)
        .order_by(Note.id)
    )
    if status:
        statement = statement.where(Note.status == status)
    async with engine.connect() as connection:
        return [NoteSummary(*row) for row in await connection.execute(statement)]


async def version_detail(
    engine: AsyncEngine, note_id: int, version: int
) -> tuple[VersionText, list[CitationRow], list[ClaimRow]]:
    async with engine.connect() as connection:
        version_id, title, body, why_it_matters = (
            await connection.execute(
                select(
                    NoteVersion.id, NoteVersion.title, NoteVersion.body, NoteVersion.why_it_matters
                ).where(NoteVersion.note_id == note_id, NoteVersion.version == version)
            )
        ).one()
        citations = [
            CitationRow(*row)
            for row in await connection.execute(
                select(
                    Citation.marker,
                    func.coalesce(Citation.document_id, 0),
                    Citation.url,
                    Citation.title,
                    Citation.publisher,
                    Citation.published_at,
                    Citation.quote,
                )
                .where(Citation.note_version_id == version_id)
                .order_by(Citation.marker)
            )
        ]
        claims = [
            ClaimRow(*row)
            for row in await connection.execute(
                select(
                    Claim.text,
                    Claim.kind,
                    Claim.markers,
                    ClaimCheck.verdict,
                    ClaimCheck.independent_origins,
                    ClaimCheck.supporting_markers,
                    ClaimCheck.rationale,
                )
                .join(ClaimCheck, ClaimCheck.claim_id == Claim.id)
                .where(Claim.note_version_id == version_id)
                .order_by(Claim.ordinal)
            )
        ]
    return VersionText(title, body, why_it_matters), citations, claims
