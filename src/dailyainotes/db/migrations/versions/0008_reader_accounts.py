"""Reader accounts: readers, sign-in codes, sessions and the topics a reader follows (ADR 0003).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-15
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def timestamp(name: str, *, now: bool = False, nullable: bool = False) -> sa.Column[datetime]:
    default = sa.func.now() if now else None
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "readers",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        timestamp("created_at", now=True),
        timestamp("last_seen_at", now=True),
        sa.UniqueConstraint("email", name="uq_readers_email"),
    )
    op.create_table(
        "sign_in_codes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("code_digest", sa.String(64), nullable=False),
        sa.Column("link_digest", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        timestamp("expires_at"),
        timestamp("used_at", nullable=True),
        timestamp("created_at", now=True),
        sa.UniqueConstraint("link_digest", name="uq_sign_in_codes_link_digest"),
    )
    op.create_index("ix_sign_in_codes_email", "sign_in_codes", ["email"])
    op.create_table(
        "reader_sessions",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column(
            "reader_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "readers.id", ondelete="CASCADE", name="fk_reader_sessions_reader_id_readers"
            ),
            nullable=False,
        ),
        timestamp("expires_at"),
        timestamp("created_at", now=True),
        timestamp("last_used_at", now=True),
    )
    op.create_index("ix_reader_sessions_reader_id", "reader_sessions", ["reader_id"])
    op.create_table(
        "reader_topics",
        sa.Column(
            "reader_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "readers.id", ondelete="CASCADE", name="fk_reader_topics_reader_id_readers"
            ),
            primary_key=True,
        ),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE", name="fk_reader_topics_topic_id_topics"),
            primary_key=True,
        ),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.CheckConstraint("slot BETWEEN 1 AND 8", name="ck_reader_topics_slot"),
    )


def downgrade() -> None:
    op.drop_table("reader_topics")
    op.drop_table("reader_sessions")
    op.drop_table("sign_in_codes")
    op.drop_table("readers")
