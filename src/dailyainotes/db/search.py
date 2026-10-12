"""Search candidates over source chunks: full text and vectors, each best first."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select, text

from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.tables import Chunk, Document, Publisher, Topic, TopicSource


@dataclass(frozen=True)
class ChunkRecord:
    id: int
    document_id: int
    ordinal: int
    text: str
    title: str
    url: str
    publisher: str | None
    published_at: datetime | None
    text_policy: str


def in_topics(query: Select[int], topic_slugs: list[str] | None) -> Select[int]:
    """Only chunks of documents found by a source of one of these topics."""
    if not topic_slugs:
        return query
    in_topic = (
        select(TopicSource.source_id)
        .join(Topic, Topic.id == TopicSource.topic_id)
        .where(Topic.slug.in_(topic_slugs))
    )
    return query.join(Document, Document.id == Chunk.document_id).where(
        Document.source_id.in_(in_topic)
    )


async def full_text_candidates(
    engine: AsyncEngine, query: str, *, topic_slugs: list[str] | None, limit: int
) -> list[int]:
    tsquery = func.websearch_to_tsquery("english", query)
    statement = in_topics(
        select(Chunk.id)
        .where(Chunk.tsv.bool_op("@@")(tsquery))
        .order_by(func.ts_rank_cd(Chunk.tsv, tsquery).desc(), Chunk.id)
        .limit(limit),
        topic_slugs,
    )
    async with engine.connect() as connection:
        return list((await connection.execute(statement)).scalars())


async def vector_candidates(
    engine: AsyncEngine, embedding: list[float], *, topic_slugs: list[str] | None, limit: int
) -> list[int]:
    statement = in_topics(
        select(Chunk.id)
        .order_by(Chunk.embedding.cosine_distance(embedding), Chunk.id)
        .limit(limit),
        topic_slugs,
    )
    async with engine.begin() as connection:
        if topic_slugs:
            # pgvector 0.8: keep scanning the HNSW index until enough rows pass the filter,
            # instead of filtering one batch of neighbours and returning too few.
            await connection.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
        return list((await connection.execute(statement)).scalars())


async def chunks_by_id(engine: AsyncEngine, ids: list[int]) -> dict[int, ChunkRecord]:
    if not ids:
        return {}
    statement = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.ordinal,
            Chunk.text,
            Document.title,
            Document.url,
            Publisher.name,
            Document.published_at,
            Document.text_policy,
        )
        .join(Document, Document.id == Chunk.document_id)
        .outerjoin(Publisher, Publisher.id == Document.publisher_id)
        .where(Chunk.id.in_(ids))
    )
    async with engine.connect() as connection:
        rows = await connection.execute(statement)
        return {row.id: ChunkRecord(*row) for row in rows}
