"""Runs, the model usage ledger, Topic Planner proposals, and a schema for LangGraph.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LangGraph's checkpointer creates and migrates its own tables here (db/checkpoints.py),
    # outside what the drift test compares.
    op.execute("CREATE SCHEMA IF NOT EXISTS langgraph")
    op.create_table(
        "topic_profiles",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column(
            "topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="proposed", nullable=False),
        sa.Column("profile", JSONB(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_comment", sa.Text(), server_default="", nullable=False),
        sa.UniqueConstraint("topic_id", "version"),
        sa.CheckConstraint("status IN ('proposed', 'approved', 'rejected')", name="status"),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("thread_id", sa.Text()),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(16), server_default="running", nullable=False),
        sa.Column("error", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('plan', 'edition', 'story', 'ask', 'eval')", name="kind"),
        sa.CheckConstraint("status IN ('running', 'waiting', 'done', 'failed')", name="status"),
    )
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("agent_runs.id", ondelete="SET NULL")),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("fell_back", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("error", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_table("agent_runs")
    op.drop_table("topic_profiles")
    op.execute("DROP SCHEMA IF EXISTS langgraph CASCADE")
