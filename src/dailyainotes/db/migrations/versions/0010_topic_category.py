"""A category per topic, for its cover and its group in the topic picker (DESIGN.md, Covers).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("category", sa.String(16)))
    op.create_check_constraint(
        "ck_topics_category",
        "topics",
        "category IN ('motorsport', 'sport', 'science', 'climate', 'business', 'technology', "
        "'culture')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_topics_category", "topics", type_="check")
    op.drop_column("topics", "category")
