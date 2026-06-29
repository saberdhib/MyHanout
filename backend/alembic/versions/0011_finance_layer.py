"""Couche financière : catégories de charges + classification facture + feedback.

Revision ID: 0011_finance_layer
Revises: 0010_promo_visual
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_finance_layer"
down_revision: str | None = "0010_promo_visual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Référentiel global inséré au upgrade (cohérent avec intelligence/finance/categories.py).
_CATEGORIES = [
    ("MERCHANDISE", "Marchandises / Stock", "opex", "607"),
    ("TELECOM", "Téléphonie / Internet", "opex", "626"),
    ("ENERGY", "Énergie (élec/gaz/eau)", "opex", "606"),
    ("RENT", "Loyer / Charges locatives", "opex", "613"),
    ("SUPPLIES", "Consommables / Fournitures", "opex", "606"),
    ("INSURANCE", "Assurance", "opex", "616"),
    ("MAINTENANCE", "Entretien / Réparations", "opex", "615"),
    ("SERVICES", "Services / Honoraires", "opex", "622"),
    ("TAXES", "Taxes / Cotisations", "opex", "63"),
    ("EQUIPMENT", "Matériel / Équipement", "capex", "215"),
    ("OTHER", "Autre", "opex", None),
]


def upgrade() -> None:
    now = sa.func.now()
    category = op.create_table(
        "expense_category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="opex"),
        sa.Column("accounting_hint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_expense_category_code", "expense_category", ["code"], unique=True)

    op.bulk_insert(
        category,
        [
            {"code": c, "label": label, "kind": kind, "accounting_hint": hint}
            for c, label, kind, hint in _CATEGORIES
        ],
    )

    # Colonnes de classification sur la facture.
    op.add_column("invoice", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column(
        "invoice",
        sa.Column("expense_kind", sa.String(length=16), nullable=False, server_default="unknown"),
    )
    op.add_column("invoice", sa.Column("classification_source", sa.String(length=16), nullable=True))
    op.add_column("invoice", sa.Column("classification_confidence", sa.Numeric(4, 3), nullable=True))
    op.add_column("invoice", sa.Column("classification_explanation", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_invoice_category", "invoice", "expense_category", ["category_id"], ["id"]
    )

    # Retours de classification (tenant-scopé).
    op.create_table(
        "expense_classification_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoice.id"), nullable=False),
        sa.Column(
            "previous_category_id", sa.Integer(), sa.ForeignKey("expense_category.id"), nullable=True
        ),
        sa.Column(
            "new_category_id", sa.Integer(), sa.ForeignKey("expense_category.id"), nullable=True
        ),
        sa.Column("previous_kind", sa.String(length=16), nullable=True),
        sa.Column("new_kind", sa.String(length=16), nullable=True),
        sa.Column("previous_source", sa.String(length=16), nullable=True),
        sa.Column("corrected_by_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "ix_ecf_organization_id", "expense_classification_feedback", ["organization_id"]
    )
    op.create_index("ix_ecf_invoice_id", "expense_classification_feedback", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_ecf_invoice_id", table_name="expense_classification_feedback")
    op.drop_index("ix_ecf_organization_id", table_name="expense_classification_feedback")
    op.drop_table("expense_classification_feedback")

    op.drop_constraint("fk_invoice_category", "invoice", type_="foreignkey")
    op.drop_column("invoice", "classification_explanation")
    op.drop_column("invoice", "classification_confidence")
    op.drop_column("invoice", "classification_source")
    op.drop_column("invoice", "expense_kind")
    op.drop_column("invoice", "category_id")

    op.drop_index("ix_expense_category_code", table_name="expense_category")
    op.drop_table("expense_category")
