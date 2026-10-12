"""Ingestion: topics, publishers, sources, documents and their searchable chunks.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("controversial", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('draft', 'active', 'paused')", name="status"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "publishers",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("owner_group", sa.String(253), nullable=False),
        sa.Column("trust_prior", sa.Float(), nullable=False),
        sa.Column("paywalled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('primary', 'wire', 'editorial', 'specialist', 'user_generated', 'unknown')",
            name="kind",
        ),
        sa.UniqueConstraint("domain"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("config", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "publisher_id", sa.Integer(), sa.ForeignKey("publishers.id", ondelete="SET NULL")
        ),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("error_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("etag", sa.Text()),
        sa.Column("last_modified", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "type IN ('rss', 'arxiv', 'github_releases', 'hackernews')", name="type"
        ),
        sa.CheckConstraint("status IN ('active', 'paused')", name="status"),
        sa.UniqueConstraint("locator"),
    )
    op.create_table(
        "topic_sources",
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url_hash", sa.String(64), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL")),
        sa.Column(
            "publisher_id", sa.Integer(), sa.ForeignKey("publishers.id", ondelete="SET NULL")
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("lead", sa.Text(), server_default="", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("text_policy", sa.String(16), nullable=False),
        sa.Column("policy_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("content_purge_after", sa.DateTime(timezone=True)),
        sa.CheckConstraint("text_policy IN ('full', 'summary', 'link_only')", name="text_policy"),
        sa.UniqueConstraint("canonical_url_hash"),
    )
    op.create_index("ix_documents_published_at", "documents", ["published_at"])
    op.create_table(
        "chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "tsv",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=False,
        ),
        sa.UniqueConstraint("document_id", "ordinal"),
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index(
        "ix_chunks_embedding",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("topic_sources")
    op.drop_table("sources")
    op.drop_table("publishers")
    op.drop_table("topics")
