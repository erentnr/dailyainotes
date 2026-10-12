"""Search columns on notes, the Ask log, rate limits and eval runs.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def created_at() -> sa.Column[datetime]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.add_column("notes", sa.Column("search_text", sa.Text()))
    op.add_column("notes", sa.Column("embedding", Vector(384)))
    op.add_column(
        "notes",
        sa.Column(
            "tsv",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', coalesce(search_text, ''))", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("ix_notes_tsv", "notes", ["tsv"], postgresql_using="gin")
    op.create_index(
        "ix_notes_embedding",
        "notes",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "ask_requests",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("cited_note_ids", ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("insufficient", sa.Boolean(), nullable=False),
        created_at(),
    )
    op.create_index("ix_ask_requests_created_at", "ask_requests", ["created_at"])
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("suite", sa.String(32), nullable=False),
        sa.Column("git_sha", sa.String(40), server_default="", nullable=False),
        sa.Column("metrics", JSONB(), nullable=False),
        created_at(),
    )


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_table("rate_limits")
    op.drop_table("ask_requests")
    op.drop_index("ix_notes_embedding", table_name="notes")
    op.drop_index("ix_notes_tsv", table_name="notes")
    op.drop_column("notes", "tsv")
    op.drop_column("notes", "embedding")
    op.drop_column("notes", "search_text")
