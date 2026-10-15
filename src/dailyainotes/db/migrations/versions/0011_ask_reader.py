"""Ask needs an account (ADR 0004): each question keeps its reader and goes with the account.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ask_requests",
        sa.Column(
            "reader_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "readers.id", ondelete="CASCADE", name="fk_ask_requests_reader_id_readers"
            ),
        ),
    )
    op.create_index("ix_ask_requests_reader_id", "ask_requests", ["reader_id"])


def downgrade() -> None:
    op.drop_index("ix_ask_requests_reader_id", "ask_requests")
    op.drop_column("ask_requests", "reader_id")
