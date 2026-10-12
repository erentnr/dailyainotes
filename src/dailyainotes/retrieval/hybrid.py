"""Hybrid search: full text and vectors from Postgres, merged by reciprocal rank fusion, then
an optional reranker."""

from dataclasses import dataclass
from typing import Protocol

from langchain_core.embeddings import Embeddings

from dailyainotes.db import search as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.domain.rank_fusion import reciprocal_rank_fusion

# Candidates each method returns before fusion.
CANDIDATES = 40


@dataclass(frozen=True)
class SearchHit:
    chunk: db.ChunkRecord
    score: float
    full_text_rank: int | None
    vector_rank: int | None


class Reranker(Protocol):
    async def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]: ...


class KeepOrder:
    """The default: rank fusion's order, unchanged."""

    async def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        return hits


async def hybrid_search(
    engine: AsyncEngine,
    embeddings: Embeddings,
    query: str,
    *,
    topic_slugs: list[str] | None = None,
    limit: int = 8,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    vector = await embeddings.aembed_query(query)
    full_text = await db.full_text_candidates(
        engine, query, topic_slugs=topic_slugs, limit=CANDIDATES
    )
    nearest = await db.vector_candidates(engine, vector, topic_slugs=topic_slugs, limit=CANDIDATES)
    fused = reciprocal_rank_fusion({"full_text": full_text, "vector": nearest})
    chunks = await db.chunks_by_id(engine, [f.id for f in fused])
    hits = [
        SearchHit(chunks[f.id], f.score, f.ranks.get("full_text"), f.ranks.get("vector"))
        for f in fused
    ]
    return (await (reranker or KeepOrder()).rerank(query, hits))[:limit]


@dataclass(frozen=True)
class NoteHit:
    note: db.NoteRecord
    score: float
    full_text_rank: int | None
    vector_rank: int | None
    # Cosine similarity to the question, when the note was among the nearest.
    similarity: float | None


async def search_notes(
    engine: AsyncEngine,
    embeddings: Embeddings,
    query: str,
    *,
    topic_slugs: list[str] | None = None,
    limit: int = 8,
) -> list[NoteHit]:
    """Published notes, by the same fusion of full text and vectors as source search."""
    vector = await embeddings.aembed_query(query)
    full_text = await db.note_full_text_candidates(
        engine, query, topic_slugs=topic_slugs, limit=CANDIDATES
    )
    nearest = await db.note_vector_candidates(
        engine, vector, topic_slugs=topic_slugs, limit=CANDIDATES
    )
    similarity = dict(nearest)
    fused = reciprocal_rank_fusion(
        {"full_text": full_text, "vector": [note_id for note_id, _ in nearest]}
    )[:limit]
    notes = await db.notes_by_id(engine, [f.id for f in fused])
    return [
        NoteHit(
            notes[f.id],
            f.score,
            f.ranks.get("full_text"),
            f.ranks.get("vector"),
            similarity.get(f.id),
        )
        for f in fused
    ]
