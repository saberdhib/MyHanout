"""Champs de revue/idempotence sur invoice (Phase 1).

Revision ID: 0002_invoice_review
Revises: 0001_initial
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_invoice_review"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoice", sa.Column("file_hash", sa.String(64), nullable=True))
    op.add_column("invoice", sa.Column("validation_report", sa.Text(), nullable=True))
    op.add_column("invoice", sa.Column("ocr_confidence", sa.Numeric(4, 3), nullable=True))
    op.add_column("invoice", sa.Column("reviewed_by_id", sa.Integer(), nullable=True))
    op.add_column(
        "invoice", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("invoice", sa.Column("review_reason", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_invoice_file_hash", "invoice", ["file_hash"])
    op.create_foreign_key(
        "fk_invoice_reviewed_by", "invoice", "user", ["reviewed_by_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_invoice_reviewed_by", "invoice", type_="foreignkey")
    op.drop_constraint("uq_invoice_file_hash", "invoice", type_="unique")
    op.drop_column("invoice", "review_reason")
    op.drop_column("invoice", "reviewed_at")
    op.drop_column("invoice", "reviewed_by_id")
    op.drop_column("invoice", "ocr_confidence")
    op.drop_column("invoice", "validation_report")
    op.drop_column("invoice", "file_hash")
