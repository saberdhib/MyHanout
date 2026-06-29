"""Mémoire d'agent (tenant-scopée) — gaps techniques.

Revision ID: 0006_agent_memory
Revises: 0005_tenant_phase2
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_agent_memory"
down_revision: str | None = "0005_tenant_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_memory",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(128), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_memory_organization_id", "agent_memory", ["organization_id"])
    op.create_index("ix_agent_memory_agent", "agent_memory", ["agent"])
    op.create_index("ix_agent_memory_subject", "agent_memory", ["subject"])


def downgrade() -> None:
    op.drop_table("agent_memory")
