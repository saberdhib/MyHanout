"""Omni-accès : équipements + relevés de température + réf. caisse sur les ventes.

Revision ID: 0012_omni_access
Revises: 0011_finance_layer
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_omni_access"
down_revision: str | None = "0011_finance_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="fridge"),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("min_temp_c", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("max_temp_c", sa.Numeric(5, 2), nullable=False, server_default="4"),
        sa.Column("sensor_external_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_equipment_organization_id", "equipment", ["organization_id"])
    op.create_index("ix_equipment_sensor_external_id", "equipment", ["sensor_external_id"])

    op.create_table(
        "temperature_reading",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column(
            "equipment_id",
            sa.Integer(),
            sa.ForeignKey("equipment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("temp_c", sa.Numeric(5, 2), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="mock"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_tr_organization_id", "temperature_reading", ["organization_id"])
    op.create_index("ix_tr_equipment_id", "temperature_reading", ["equipment_id"])
    op.create_index("ix_tr_recorded_at", "temperature_reading", ["recorded_at"])

    # Référence ticket caisse (idempotence de l'ingestion POS).
    op.add_column("sale", sa.Column("external_ref", sa.String(length=64), nullable=True))
    op.create_index("ix_sale_external_ref", "sale", ["external_ref"])


def downgrade() -> None:
    op.drop_index("ix_sale_external_ref", table_name="sale")
    op.drop_column("sale", "external_ref")

    op.drop_index("ix_tr_recorded_at", table_name="temperature_reading")
    op.drop_index("ix_tr_equipment_id", table_name="temperature_reading")
    op.drop_index("ix_tr_organization_id", table_name="temperature_reading")
    op.drop_table("temperature_reading")

    op.drop_index("ix_equipment_sensor_external_id", table_name="equipment")
    op.drop_index("ix_equipment_organization_id", table_name="equipment")
    op.drop_table("equipment")
