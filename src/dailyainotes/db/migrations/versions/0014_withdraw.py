"""A published note can be withdrawn, and the withdrawal is kept with the decisions (ADR 0008).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-22
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Each constraint only widens, so the previous image keeps working during a deploy. op.f
    # keeps the naming convention from prefixing the full names a second time.
    op.drop_constraint(op.f("ck_notes_status"), "notes", type_="check")
    op.create_check_constraint(
        op.f("ck_notes_status"),
        "notes",
        "status IN ('drafting', 'awaiting_approval', 'published', 'rejected', 'withdrawn')",
    )
    op.drop_constraint(op.f("ck_approvals_decision"), "approvals", type_="check")
    op.create_check_constraint(
        op.f("ck_approvals_decision"), "approvals", "decision IN ('approve', 'reject', 'withdraw')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_approvals_decision"), "approvals", type_="check")
    op.create_check_constraint(
        op.f("ck_approvals_decision"), "approvals", "decision IN ('approve', 'reject')"
    )
    op.drop_constraint(op.f("ck_notes_status"), "notes", type_="check")
    op.create_check_constraint(
        op.f("ck_notes_status"),
        "notes",
        "status IN ('drafting', 'awaiting_approval', 'published', 'rejected')",
    )
