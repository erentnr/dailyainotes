"""Topic suggestions from readers, accepted or declined by the editor (ADR 0003).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topic_suggestions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "reader_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "readers.id", ondelete="CASCADE", name="fk_topic_suggestions_reader_id_readers"
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey(
                "topics.id", ondelete="SET NULL", name="fk_topic_suggestions_topic_id_topics"
            ),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'accepted', 'declined')", name="ck_topic_suggestions_status"
        ),
    )
    op.create_index("ix_topic_suggestions_reader_id", "topic_suggestions", ["reader_id"])


def downgrade() -> None:
    op.drop_table("topic_suggestions")
