"""Ouverture : clés API + webhooks sortants (n8n / Make / Zapier).

Tables tenant : api_key (accès programmatique, hash + préfixe), webhook_endpoint
(livraisons signées HMAC). Réversible.

Revision ID: 0016_api_keys_webhooks
Revises: 0015_data_platform
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_api_keys_webhooks"
down_revision: str | None = "0015_data_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.String(length=255), nullable=False, server_default="*"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_api_key_organization_id", "api_key", ["organization_id"])
    op.create_index("ix_api_key_prefix", "api_key", ["prefix"])
    op.create_index("ix_api_key_key_hash", "api_key", ["key_hash"])

    op.create_table(
        "webhook_endpoint",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("events", sa.String(length=255), nullable=False, server_default="*"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("last_status", sa.Integer(), nullable=True),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_webhook_endpoint_organization_id", "webhook_endpoint", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_webhook_endpoint_organization_id", table_name="webhook_endpoint")
    op.drop_table("webhook_endpoint")
    op.drop_index("ix_api_key_key_hash", table_name="api_key")
    op.drop_index("ix_api_key_prefix", table_name="api_key")
    op.drop_index("ix_api_key_organization_id", table_name="api_key")
    op.drop_table("api_key")
