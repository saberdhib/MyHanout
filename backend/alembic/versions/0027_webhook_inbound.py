"""Idempotence des webhooks entrants : webhook_inbound (global).

Revision ID: 0027_webhook_inbound
Revises: 0026_model_registry
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_webhook_inbound"
down_revision: str | None = "0026_model_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_inbound",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "external_id", name="uq_webhook_inbound_source_ext"),
    )
    op.create_index("ix_webhook_inbound_source", "webhook_inbound", ["source"])
    op.create_index("ix_webhook_inbound_external_id", "webhook_inbound", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_webhook_inbound_external_id", table_name="webhook_inbound")
    op.drop_index("ix_webhook_inbound_source", table_name="webhook_inbound")
    op.drop_table("webhook_inbound")
