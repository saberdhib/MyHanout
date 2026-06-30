"""Démarque anti-gaspillage : table markdown_suggestion (tenant, explicable).

Suggestions de démarque produites par l'agent Démarque : lot périssable à risque,
remise proposée, impact (marge récupérée / perte évitée), statut human-in-the-loop.
Réversible.

Revision ID: 0017_markdown
Revises: 0016_api_keys_webhooks
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_markdown"
down_revision: str | None = "0016_api_keys_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "markdown_suggestion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("stock.id"), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("quantity_at_risk", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("days_to_expiry", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("suggested_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_units_cleared", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recovered_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avoided_loss", sa.Float(), nullable=False, server_default="0"),
        sa.Column("baseline_loss", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="suggested"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("data_used", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index(
        "ix_markdown_suggestion_organization_id", "markdown_suggestion", ["organization_id"]
    )
    op.create_index("ix_markdown_suggestion_product_id", "markdown_suggestion", ["product_id"])
    op.create_index("ix_markdown_suggestion_stock_id", "markdown_suggestion", ["stock_id"])
    op.create_index(
        "ix_markdown_suggestion_pipeline_run_id", "markdown_suggestion", ["pipeline_run_id"]
    )
    op.create_index("ix_markdown_suggestion_expiry_date", "markdown_suggestion", ["expiry_date"])
    op.create_index("ix_markdown_suggestion_status", "markdown_suggestion", ["status"])


def downgrade() -> None:
    op.drop_index("ix_markdown_suggestion_status", table_name="markdown_suggestion")
    op.drop_index("ix_markdown_suggestion_expiry_date", table_name="markdown_suggestion")
    op.drop_index("ix_markdown_suggestion_pipeline_run_id", table_name="markdown_suggestion")
    op.drop_index("ix_markdown_suggestion_stock_id", table_name="markdown_suggestion")
    op.drop_index("ix_markdown_suggestion_product_id", table_name="markdown_suggestion")
    op.drop_index("ix_markdown_suggestion_organization_id", table_name="markdown_suggestion")
    op.drop_table("markdown_suggestion")
