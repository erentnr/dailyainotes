"""Table definitions. Alembic migrations must create exactly these (see the drift test)."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable constraint names, so hand-written migrations can refer to them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# BAAI/bge-small-en-v1.5 (INTENT.md, Architectural Constraints). Changing it means re-embedding.
EMBEDDING_DIMENSIONS = 384


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (CheckConstraint("status IN ('draft', 'active', 'paused')", name="status"),)

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default="draft")
    controversial: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Publisher(Base):
    __tablename__ = "publishers"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('primary', 'wire', 'editorial', 'specialist', 'user_generated', 'unknown')",
            name="kind",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    domain: Mapped[str] = mapped_column(String(253), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    # Publishers with the same owner group are not independent of each other.
    owner_group: Mapped[str] = mapped_column(String(253))
    trust_prior: Mapped[float] = mapped_column(Float)
    paywalled: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("type IN ('rss', 'arxiv', 'github_releases', 'hackernews')", name="type"),
        CheckConstraint("status IN ('active', 'paused')", name="status"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    # What the connector fetches: a feed URL, an arXiv query, owner/repo, an HN query.
    locator: Mapped[str] = mapped_column(Text, unique=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    publisher_id: Mapped[int | None] = mapped_column(
        ForeignKey("publishers.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(16), server_default="active")
    error_streak: Mapped[int] = mapped_column(server_default=text("0"))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TopicSource(Base):
    __tablename__ = "topic_sources"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("text_policy IN ('full', 'summary', 'link_only')", name="text_policy"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    canonical_url_hash: Mapped[str] = mapped_column(String(64), unique=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    publisher_id: Mapped[int | None] = mapped_column(
        ForeignKey("publishers.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text)
    # The publisher's own description or abstract; shown with link-only documents too.
    lead: Mapped[str] = mapped_column(Text, server_default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # full: page text we may summarize; summary: only feed or API text; link_only: opted out.
    text_policy: Mapped[str] = mapped_column(String(16))
    policy_reason: Mapped[str] = mapped_column(Text, server_default="")
    # Internal only, never served; purged after 30 days (INTENT.md, Architectural Constraints).
    content: Mapped[str | None] = mapped_column(Text)
    content_purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "ordinal"),
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    # Chunk 0 is the title and lead; later chunks come from page text (full policy only).
    ordinal: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )
