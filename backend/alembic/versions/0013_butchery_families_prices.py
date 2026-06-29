"""Familles produit + historique des prix + boucherie (lots/coupes, traçabilité).

Revision ID: 0013_butchery_families_prices
Revises: 0012_omni_access
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_butchery_families_prices"
down_revision: str | None = "0012_omni_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = sa.func.now()

    # Famille produit (notion de regroupement).
    op.add_column("product", sa.Column("family", sa.String(length=64), nullable=True))
    op.create_index("ix_product_family", "product", ["family"])

    # Historique des prix (achat/vente dans le temps).
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_ph_organization_id", "price_history", ["organization_id"])
    op.create_index("ix_ph_product_id", "price_history", ["product_id"])
    op.create_index("ix_ph_kind", "price_history", ["kind"])
    op.create_index("ix_ph_effective_at", "price_history", ["effective_at"])

    # Boucherie : lots (bête au poids).
    op.create_table(
        "meat_lot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("lot_code", sa.String(length=64), nullable=False),
        sa.Column("species", sa.String(length=16), nullable=False, server_default="boeuf"),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("supplier.id"), nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(10, 3), nullable=False),
        sa.Column("purchase_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="received"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_meat_lot_organization_id", "meat_lot", ["organization_id"])
    op.create_index("ix_meat_lot_lot_code", "meat_lot", ["lot_code"])
    op.create_index("ix_meat_lot_received_at", "meat_lot", ["received_at"])

    # Boucherie : coupes (pièces issues d'un lot).
    op.create_table(
        "meat_cut",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column(
            "lot_id", sa.Integer(), sa.ForeignKey("meat_lot.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=True),
        sa.Column("cut_label", sa.String(length=128), nullable=False),
        sa.Column("expected_weight_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("actual_weight_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("is_waste", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_meat_cut_organization_id", "meat_cut", ["organization_id"])
    op.create_index("ix_meat_cut_lot_id", "meat_cut", ["lot_id"])


def downgrade() -> None:
    op.drop_index("ix_meat_cut_lot_id", table_name="meat_cut")
    op.drop_index("ix_meat_cut_organization_id", table_name="meat_cut")
    op.drop_table("meat_cut")

    op.drop_index("ix_meat_lot_received_at", table_name="meat_lot")
    op.drop_index("ix_meat_lot_lot_code", table_name="meat_lot")
    op.drop_index("ix_meat_lot_organization_id", table_name="meat_lot")
    op.drop_table("meat_lot")

    op.drop_index("ix_ph_effective_at", table_name="price_history")
    op.drop_index("ix_ph_kind", table_name="price_history")
    op.drop_index("ix_ph_product_id", table_name="price_history")
    op.drop_index("ix_ph_organization_id", table_name="price_history")
    op.drop_table("price_history")

    op.drop_index("ix_product_family", table_name="product")
    op.drop_column("product", "family")
