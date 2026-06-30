"""Connecteurs par commerce (modèle B) : table tenant_connector (secrets chiffrés).

Réversible.

Revision ID: 0020_tenant_connectors
Revises: 0019_briefing
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_tenant_connectors"
down_revision: str | None = "0019_briefing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "tenant_connector",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("config", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("secret_enc", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_tenant_connector_organization_id", "tenant_connector", ["organization_id"])
    op.create_index("ix_tenant_connector_kind", "tenant_connector", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_tenant_connector_kind", table_name="tenant_connector")
    op.drop_index("ix_tenant_connector_organization_id", table_name="tenant_connector")
    op.drop_table("tenant_connector")
