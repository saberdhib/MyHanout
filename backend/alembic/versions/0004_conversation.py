"""Table conversation (machine à états WhatsApp) — Phase 2.

Revision ID: 0004_conversation
Revises: 0003_phase2_loop
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_conversation"
down_revision: str | None = "0003_phase2_loop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone", sa.String(32), nullable=False, unique=True),
        sa.Column("state", sa.String(48), server_default="idle"),
        sa.Column("context", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversation_phone", "conversation", ["phone"])


def downgrade() -> None:
    op.drop_table("conversation")
