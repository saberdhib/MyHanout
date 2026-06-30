"""Signaux externes (météo/vacances/carburant/foot) pour le forecasting.

Tables globales (données publiques, non tenant) : registre + observations.

Revision ID: 0014_external_signals
Revises: 0013_butchery_families_prices
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_external_signals"
down_revision: str | None = "0013_butchery_families_prices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFS = [
    ("weather_temp_c", "Température (°C)", "weather", "°C"),
    ("weather_rain", "Pluie (0/1)", "weather", "bool"),
    ("school_holiday", "Vacances scolaires (0/1)", "holiday", "bool"),
    ("public_holiday", "Jour férié (0/1)", "holiday", "bool"),
    ("fuel_price_eur_l", "Prix carburant (€/L)", "fuel", "€/L"),
    ("football_match", "Match de foot local (0/1)", "sports", "bool"),
]


def upgrade() -> None:
    now = sa.func.now()
    definition = op.create_table(
        "signal_definition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=48), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="custom"),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="mock"),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("ix_signal_definition_key", "signal_definition", ["key"], unique=True)
    op.bulk_insert(
        definition,
        [
            {"key": k, "label": label, "kind": kind, "unit": unit, "provider": "mock"}
            for k, label, kind, unit in _DEFS
        ],
    )

    op.create_table(
        "signal_observation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_key", sa.String(length=48), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=True),
        sa.Column("obs_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("value_text", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("signal_key", "region", "obs_date", name="uq_signal_obs"),
    )
    op.create_index("ix_signal_observation_signal_key", "signal_observation", ["signal_key"])
    op.create_index("ix_signal_observation_region", "signal_observation", ["region"])
    op.create_index("ix_signal_observation_obs_date", "signal_observation", ["obs_date"])


def downgrade() -> None:
    op.drop_index("ix_signal_observation_obs_date", table_name="signal_observation")
    op.drop_index("ix_signal_observation_region", table_name="signal_observation")
    op.drop_index("ix_signal_observation_signal_key", table_name="signal_observation")
    op.drop_table("signal_observation")
    op.drop_index("ix_signal_definition_key", table_name="signal_definition")
    op.drop_table("signal_definition")
