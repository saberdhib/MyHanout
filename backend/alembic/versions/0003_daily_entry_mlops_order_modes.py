"""daily_entry + forecast_evaluation + modes de commande (Phase 2).

Revision ID: 0003_phase2_loop
Revises: 0002_invoice_review
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_phase2_loop"
# Re-chaîné après 0003_multitenant lors de la consolidation des branches.
down_revision: str | None = "0003_multitenant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # --- Saisie de fin de journée ---
    op.create_table(
        "daily_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id"), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("quantity_ordered", sa.Numeric(10, 2), server_default="0"),
        sa.Column("stock_remaining", sa.Numeric(10, 2), server_default="0"),
        sa.Column("source", sa.String(16), server_default="manual"),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("user.id")),
        *_ts(),
        sa.UniqueConstraint("product_id", "entry_date", name="uq_daily_entry_product_date"),
    )
    op.create_index("ix_daily_entry_product_id", "daily_entry", ["product_id"])
    op.create_index("ix_daily_entry_entry_date", "daily_entry", ["entry_date"])

    # --- Évaluation de prévision (MLOps) ---
    op.create_table(
        "forecast_evaluation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id"), nullable=False),
        sa.Column("eval_date", sa.Date, nullable=False),
        sa.Column("predicted", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual", sa.Numeric(12, 2), nullable=False),
        sa.Column("error_abs", sa.Numeric(12, 4), nullable=False),
        sa.Column("error_pct", sa.Numeric(8, 4)),
        sa.Column("model", sa.String(32), nullable=False),
        sa.Column("model_version", sa.String(64), server_default="v1"),
        *_ts(),
        sa.UniqueConstraint(
            "product_id", "eval_date", "model", name="uq_forecast_eval_product_date_model"
        ),
    )
    op.create_index("ix_forecast_eval_product_id", "forecast_evaluation", ["product_id"])
    op.create_index("ix_forecast_eval_eval_date", "forecast_evaluation", ["eval_date"])

    # --- Commande : modes d'action + suggestion ---
    op.add_column(
        "order",
        sa.Column("action_mode", sa.String(32), server_default="record_only", nullable=True),
    )
    op.add_column("order", sa.Column("supplier_message", sa.Text()))
    op.add_column("order", sa.Column("sent_at", sa.DateTime(timezone=True)))
    op.add_column("order", sa.Column("suggestion_rationale", sa.Text()))

    # --- Fournisseur : délai + mode par défaut ---
    op.add_column(
        "supplier", sa.Column("lead_time_days", sa.Integer(), server_default="1", nullable=True)
    )
    op.add_column(
        "supplier",
        sa.Column("default_order_mode", sa.String(32), server_default="record_only", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supplier", "default_order_mode")
    op.drop_column("supplier", "lead_time_days")
    op.drop_column("order", "suggestion_rationale")
    op.drop_column("order", "sent_at")
    op.drop_column("order", "supplier_message")
    op.drop_column("order", "action_mode")
    op.drop_table("forecast_evaluation")
    op.drop_table("daily_entry")
