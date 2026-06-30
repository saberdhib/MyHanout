"""Socle data platform : pipeline runs, signaux métier, reco, alertes, snapshots.

Toutes tenant (organization_id) sauf rien ici n'est global. Réversible.

Revision ID: 0015_data_platform
Revises: 0014_external_signals
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_data_platform"
down_revision: str | None = "0014_external_signals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str = "created_at"):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "pipeline_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("trigger", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_freshness_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_pipeline_run_organization_id", "pipeline_run", ["organization_id"])
    op.create_index("ix_pipeline_run_job_name", "pipeline_run", ["job_name"])
    op.create_index("ix_pipeline_run_status", "pipeline_run", ["status"])

    op.create_table(
        "external_signal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("key", sa.String(length=48), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="custom"),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("value_text", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="merchant"),
        sa.Column("scope", sa.String(length=32), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint("organization_id", "key", "signal_date", name="uq_external_signal"),
    )
    op.create_index("ix_external_signal_organization_id", "external_signal", ["organization_id"])
    op.create_index("ix_external_signal_key", "external_signal", ["key"])
    op.create_index("ix_external_signal_signal_date", "external_signal", ["signal_date"])

    op.create_table(
        "inventory_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reorder_threshold", sa.Float(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.UniqueConstraint(
            "organization_id", "product_id", "snapshot_date", name="uq_inventory_snapshot"
        ),
    )
    op.create_index(
        "ix_inventory_snapshot_organization_id", "inventory_snapshot", ["organization_id"]
    )
    op.create_index("ix_inventory_snapshot_product_id", "inventory_snapshot", ["product_id"])
    op.create_index("ix_inventory_snapshot_snapshot_date", "inventory_snapshot", ["snapshot_date"])

    op.create_table(
        "recommendation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("action", sa.String(length=16), nullable=False, server_default="order"),
        sa.Column("suggested_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_factor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="suggested"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("data_used", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_recommendation_organization_id", "recommendation", ["organization_id"])
    op.create_index("ix_recommendation_product_id", "recommendation", ["product_id"])
    op.create_index("ix_recommendation_pipeline_run_id", "recommendation", ["pipeline_run_id"])
    op.create_index("ix_recommendation_status", "recommendation", ["status"])

    op.create_table(
        "alert",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=12), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("rule", sa.String(length=255), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_alert_organization_id", "alert", ["organization_id"])
    op.create_index("ix_alert_kind", "alert", ["kind"])
    op.create_index("ix_alert_status", "alert", ["status"])


def downgrade() -> None:
    op.drop_index("ix_alert_status", table_name="alert")
    op.drop_index("ix_alert_kind", table_name="alert")
    op.drop_index("ix_alert_organization_id", table_name="alert")
    op.drop_table("alert")

    op.drop_index("ix_recommendation_status", table_name="recommendation")
    op.drop_index("ix_recommendation_pipeline_run_id", table_name="recommendation")
    op.drop_index("ix_recommendation_product_id", table_name="recommendation")
    op.drop_index("ix_recommendation_organization_id", table_name="recommendation")
    op.drop_table("recommendation")

    op.drop_index("ix_inventory_snapshot_snapshot_date", table_name="inventory_snapshot")
    op.drop_index("ix_inventory_snapshot_product_id", table_name="inventory_snapshot")
    op.drop_index("ix_inventory_snapshot_organization_id", table_name="inventory_snapshot")
    op.drop_table("inventory_snapshot")

    op.drop_index("ix_external_signal_signal_date", table_name="external_signal")
    op.drop_index("ix_external_signal_key", table_name="external_signal")
    op.drop_index("ix_external_signal_organization_id", table_name="external_signal")
    op.drop_table("external_signal")

    op.drop_index("ix_pipeline_run_status", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_job_name", table_name="pipeline_run")
    op.drop_index("ix_pipeline_run_organization_id", table_name="pipeline_run")
    op.drop_table("pipeline_run")
