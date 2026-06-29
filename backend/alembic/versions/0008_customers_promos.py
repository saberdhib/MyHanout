"""Clients (RGPD opt-in) + campagnes promo flash — demo pack.

Revision ID: 0008_customers_promos
Revises: 0007_doc_chunk_tenant
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_customers_promos"
down_revision: str | None = "0007_doc_chunk_tenant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("consent_opt_in", sa.Boolean, server_default=sa.false()),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
        *_ts(),
    )
    op.create_index("ix_customer_organization_id", "customer", ["organization_id"])

    op.create_table(
        "promo_campaign",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("discount_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("reason", sa.Text),
        sa.Column("status", sa.String(16), server_default="draft"),
        sa.Column("channels", sa.String(128)),
        sa.Column("audience_count", sa.Integer, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        *_ts(),
    )
    op.create_index("ix_promo_campaign_organization_id", "promo_campaign", ["organization_id"])


def downgrade() -> None:
    op.drop_table("promo_campaign")
    op.drop_table("customer")
