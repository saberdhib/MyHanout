"""Visuel d'affiche promo généré (visual_url / visual_prompt) — demo plus.

Revision ID: 0010_promo_visual
Revises: 0009_invoice_paid
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_promo_visual"
down_revision: str | None = "0009_invoice_paid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("promo_campaign", sa.Column("visual_url", sa.Text(), nullable=True))
    op.add_column("promo_campaign", sa.Column("visual_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("promo_campaign", "visual_prompt")
    op.drop_column("promo_campaign", "visual_url")
