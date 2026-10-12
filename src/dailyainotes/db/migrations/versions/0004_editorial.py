"""Editorial: editions, stories, notes and their versions, citations, claims, approvals.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def created_at(name: str = "created_at") -> sa.Column[datetime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "editions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), server_default="running", nullable=False),
        sa.Column("stats", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        created_at("started_at"),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("topic_id", "date"),
        sa.CheckConstraint("status IN ('running', 'done', 'failed')", name="status"),
    )
    op.create_table(
        "stories",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "edition_id",
            sa.BigInteger(),
            sa.ForeignKey("editions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("independent_publishers", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", JSONB(), nullable=False),
        sa.Column("picked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "story_documents",
        sa.Column(
            "story_id",
            sa.BigInteger(),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "story_id",
            sa.BigInteger(),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("edition_date", sa.Date(), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), server_default="drafting", nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("published_version", sa.Integer()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        created_at(),
        sa.UniqueConstraint("story_id"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint(
            "status IN ('drafting', 'awaiting_approval', 'published', 'rejected')", name="status"
        ),
    )
    op.create_index("ix_notes_edition_date", "notes", ["edition_date"])
    op.create_table(
        "note_versions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "note_id",
            sa.BigInteger(),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        created_at(),
        sa.UniqueConstraint("note_id", "version"),
    )
    op.create_table(
        "citations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "note_version_id",
            sa.BigInteger(),
            sa.ForeignKey("note_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("marker", sa.Integer(), nullable=False),
        sa.Column(
            "document_id", sa.BigInteger(), sa.ForeignKey("documents.id", ondelete="SET NULL")
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("quote", sa.Text(), server_default="", nullable=False),
        sa.UniqueConstraint("note_version_id", "marker"),
    )
    op.create_table(
        "claims",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "note_version_id",
            sa.BigInteger(),
            sa.ForeignKey("note_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("markers", ARRAY(sa.Integer()), nullable=False),
        sa.CheckConstraint("kind IN ('factual', 'numeric', 'attributed', 'context')", name="kind"),
    )
    op.create_table(
        "claim_checks",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "claim_id",
            sa.BigInteger(),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("independent_origins", sa.Integer(), nullable=False),
        sa.Column("supporting_markers", ARRAY(sa.Integer()), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.UniqueConstraint("claim_id"),
        sa.CheckConstraint(
            "verdict IN ('supported', 'weak', 'unsupported', 'contradicted')", name="verdict"
        ),
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "note_id",
            sa.BigInteger(),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("comment", sa.Text(), server_default="", nullable=False),
        created_at("decided_at"),
        sa.CheckConstraint("decision IN ('approve', 'reject')", name="decision"),
    )


def downgrade() -> None:
    for table in (
        "approvals",
        "claim_checks",
        "claims",
        "citations",
        "note_versions",
        "notes",
        "story_documents",
        "stories",
        "editions",
    ):
        op.drop_table(table)
