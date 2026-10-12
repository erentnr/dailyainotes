"""A schema for the Procrastinate queue.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-13
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The worker creates Procrastinate's tables here on its first start (worker.py), outside
    # what the drift test compares.
    op.execute("CREATE SCHEMA IF NOT EXISTS procrastinate")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS procrastinate CASCADE")
