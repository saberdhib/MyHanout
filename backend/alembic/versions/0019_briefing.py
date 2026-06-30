"""Briefing du matin : daily_briefing + briefing_item (tâches du jour consolidées).

Tables tenant. Réversible.

Revision ID: 0019_briefing
Revises: 0018_recipes_production
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_briefing"
down_revision: str | None = "0018_recipes_production"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "daily_briefing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("briefing_date", sa.Date(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_daily_briefing_organization_id", "daily_briefing", ["organization_id"])
    op.create_index("ix_daily_briefing_briefing_date", "daily_briefing", ["briefing_date"])
    op.create_index("ix_daily_briefing_pipeline_run_id", "daily_briefing", ["pipeline_run_id"])
    op.create_index("ix_daily_briefing_status", "daily_briefing", ["status"])

    op.create_table(
        "briefing_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("briefing_id", sa.Integer(), sa.ForeignKey("daily_briefing.id"), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=True),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_briefing_item_organization_id", "briefing_item", ["organization_id"])
    op.create_index("ix_briefing_item_briefing_id", "briefing_item", ["briefing_id"])
    op.create_index("ix_briefing_item_category", "briefing_item", ["category"])


def downgrade() -> None:
    op.drop_table("briefing_item")
    op.drop_index("ix_daily_briefing_status", table_name="daily_briefing")
    op.drop_index("ix_daily_briefing_pipeline_run_id", table_name="daily_briefing")
    op.drop_index("ix_daily_briefing_briefing_date", table_name="daily_briefing")
    op.drop_index("ix_daily_briefing_organization_id", table_name="daily_briefing")
    op.drop_table("daily_briefing")
