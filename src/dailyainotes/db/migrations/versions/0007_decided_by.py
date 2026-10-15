"""Who decided on a note or a topic plan: the editor's email from /admin, or "dan review".

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("approvals", "topic_profiles"):
        op.add_column(table, sa.Column("decided_by", sa.Text(), server_default="", nullable=False))


def downgrade() -> None:
    for table in ("approvals", "topic_profiles"):
        op.drop_column(table, "decided_by")
