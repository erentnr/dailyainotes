"""A reader's "more like this" or "less like this" on a note (ADR 0007).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "note_feedback",
        sa.Column(
            "reader_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "readers.id", ondelete="CASCADE", name="fk_note_feedback_reader_id_readers"
            ),
            primary_key=True,
        ),
        sa.Column(
            "note_id",
            sa.BigInteger(),
            sa.ForeignKey("notes.id", ondelete="CASCADE", name="fk_note_feedback_note_id_notes"),
            primary_key=True,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("value IN (-1, 1)", name="ck_note_feedback_value"),
        sa.PrimaryKeyConstraint("reader_id", "note_id", name="pk_note_feedback"),
    )


def downgrade() -> None:
    op.drop_table("note_feedback")
