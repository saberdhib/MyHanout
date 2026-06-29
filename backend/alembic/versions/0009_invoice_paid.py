"""Suivi de paiement des factures (paid / paid_at) — demo plus.

Revision ID: 0009_invoice_paid
Revises: 0008_customers_promos
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_invoice_paid"
down_revision: str | None = "0008_customers_promos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoice", sa.Column("paid", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("invoice", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("invoice", "paid_at")
    op.drop_column("invoice", "paid")
