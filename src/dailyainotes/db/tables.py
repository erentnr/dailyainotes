"""Table definitions. Alembic migrations must create exactly these (see the drift test)."""

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from dailyainotes.domain.embedding import EMBEDDING_DIMENSIONS
from dailyainotes.domain.topics import CATEGORIES

# Stable constraint names, so hand-written migrations can refer to them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'paused')", name="status"),
        CheckConstraint(f"category IN ({', '.join(repr(c) for c in CATEGORIES)})", name="category"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default="draft")
    controversial: Mapped[bool] = mapped_column(server_default=false())
    # From the catalog; NULL for a topic that came from elsewhere, such as a suggestion.
    category: Mapped[str | None] = mapped_column(String(16))
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


class TopicProfile(Base):
    """A Topic Planner proposal: keywords, entities and sources, waiting for approval."""

    __tablename__ = "topic_profiles"
    __table_args__ = (
        UniqueConstraint("topic_id", "version"),
        CheckConstraint("status IN ('proposed', 'approved', 'rejected')", name="status"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    version: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), server_default="proposed")
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # The LangGraph thread that is paused, waiting for the decision.
    thread_id: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_comment: Mapped[str] = mapped_column(Text, server_default="")
    # The editor's email from /admin, or "dan review".
    decided_by: Mapped[str] = mapped_column(Text, server_default="")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("kind IN ('plan', 'edition', 'story', 'ask', 'eval')", name="kind"),
        CheckConstraint("status IN ('running', 'waiting', 'done', 'failed')", name="status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    thread_id: Mapped[str | None] = mapped_column(Text)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), server_default="running")
    error: Mapped[str] = mapped_column(Text, server_default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LlmCall(Base):
    """One request to a model: the usage ledger behind budgets and cost per run, topic and day."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(server_default=text("0"))
    # Free plans cost nothing; the column is there for the day a paid model is approved.
    cost_usd: Mapped[float] = mapped_column(Float, server_default=text("0"))
    latency_ms: Mapped[int] = mapped_column(server_default=text("0"))
    ok: Mapped[bool]
    # True when an earlier model in the role's chain failed first.
    fell_back: Mapped[bool] = mapped_column(server_default=false())
    error: Mapped[str] = mapped_column(Text, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Edition(Base):
    """One topic's run on one day; unique, so a rerun never duplicates it."""

    __tablename__ = "editions"
    __table_args__ = (
        UniqueConstraint("topic_id", "date"),
        CheckConstraint("status IN ('running', 'done', 'failed')", name="status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), server_default="running")
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Story(Base):
    """Reports of one event, grouped by Scout, with why it was ranked where it was."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey("editions.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    document_count: Mapped[int]
    independent_publishers: Mapped[int]
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSONB)
    picked: Mapped[bool] = mapped_column(server_default=false())


class StoryDocument(Base):
    __tablename__ = "story_documents"

    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('drafting', 'awaiting_approval', 'published', 'rejected', 'withdrawn')",
            name="status",
        ),
        Index("ix_notes_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_notes_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), unique=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    edition_date: Mapped[date] = mapped_column(Date, index=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(24), server_default="drafting")
    thread_id: Mapped[str] = mapped_column(Text)
    published_version: Mapped[int | None]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set when the note is published, for Ask: its text without markers, and that text's vector.
    search_text: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', coalesce(search_text, ''))", persisted=True)
    )


class NoteVersion(Base):
    """Each draft the Writer produces; the body carries [n] citation markers."""

    __tablename__ = "note_versions"
    __table_args__ = (UniqueConstraint("note_id", "version"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    version: Mapped[int]
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    # Where independent publishers disagree, from the research brief: each point with its
    # positions and their sources (the note page's box).
    disagreements: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Citation(Base):
    """A marker's source, copied in so it survives the 30-day purge of source text."""

    __tablename__ = "citations"
    __table_args__ = (UniqueConstraint("note_version_id", "marker"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    note_version_id: Mapped[int] = mapped_column(ForeignKey("note_versions.id", ondelete="CASCADE"))
    marker: Mapped[int]
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # At most 25 words (INTENT.md, Copyright).
    quote: Mapped[str] = mapped_column(Text, server_default="")


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("kind IN ('factual', 'numeric', 'attributed', 'context')", name="kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    note_version_id: Mapped[int] = mapped_column(ForeignKey("note_versions.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))
    markers: Mapped[list[int]] = mapped_column(ARRAY(Integer))


class ClaimCheck(Base):
    __tablename__ = "claim_checks"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('supported', 'weak', 'unsupported', 'contradicted')", name="verdict"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), unique=True)
    verdict: Mapped[str] = mapped_column(String(16))
    independent_origins: Mapped[int]
    supporting_markers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    rationale: Mapped[str] = mapped_column(Text)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint("decision IN ('approve', 'reject', 'withdraw')", name="decision"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    version: Mapped[int]
    decision: Mapped[str] = mapped_column(String(16))
    comment: Mapped[str] = mapped_column(Text, server_default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # The editor's email from /admin, or "dan review".
    decided_by: Mapped[str] = mapped_column(Text, server_default="")


class AskRequest(Base):
    """One question to Ask the notes, kept 30 days (INTENT.md, Architectural Constraints)."""

    __tablename__ = "ask_requests"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # The reader who asked (ADR 0004); NULL only for questions from before accounts were needed.
    reader_id: Mapped[int | None] = mapped_column(
        ForeignKey("readers.id", ondelete="CASCADE"), index=True
    )
    ip_hash: Mapped[str] = mapped_column(String(64))
    question: Mapped[str] = mapped_column(Text)
    cited_note_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    insufficient: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class RateLimit(Base):
    """Requests per key and UTC day: a hashed IP, or `all` for the global cap."""

    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int]


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    suite: Mapped[str] = mapped_column(String(32))
    git_sha: Mapped[str] = mapped_column(String(40), server_default="")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Reader accounts (ADR 0003). Codes and session tokens are stored only as SHA-256 digests.


class Reader(Base):
    __tablename__ = "readers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SignInCode(Base):
    __tablename__ = "sign_in_codes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    code_digest: Mapped[str] = mapped_column(String(64))
    link_digest: Mapped[str] = mapped_column(String(64), unique=True)
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReaderSession(Base):
    __tablename__ = "reader_sessions"

    token_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("readers.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ReaderTopic(Base):
    __tablename__ = "reader_topics"
    __table_args__ = (CheckConstraint("slot BETWEEN 1 AND 8", name="slot"),)

    reader_id: Mapped[int] = mapped_column(
        ForeignKey("readers.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    # The topic's color slot, kept when another topic is removed (DESIGN.md, Colors).
    slot: Mapped[int] = mapped_column(Integer)


class NoteFeedback(Base):
    """A reader's "more like this" (1) or "less like this" (-1) on a note: it orders their
    daily page (ADR 0007), and goes with the account."""

    __tablename__ = "note_feedback"
    __table_args__ = (CheckConstraint("value IN (-1, 1)", name="value"),)

    reader_id: Mapped[int] = mapped_column(
        ForeignKey("readers.id", ondelete="CASCADE"), primary_key=True
    )
    note_id: Mapped[int] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TopicSuggestion(Base):
    __tablename__ = "topic_suggestions"
    __table_args__ = (CheckConstraint("status IN ('open', 'accepted', 'declined')", name="status"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("readers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(String(16), server_default="open")
    # Shown to the reader when the editor declines.
    reason: Mapped[str] = mapped_column(Text, server_default="")
    # The draft topic made when the editor accepted it.
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str] = mapped_column(Text, server_default="")
