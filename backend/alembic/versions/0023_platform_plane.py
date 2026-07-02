"""Plan plateforme (backoffice) : platform_admin, subscription, organization.status.

Tables GLOBALES (non tenant) permettant à l'opérateur MyHanout de gérer tous les
commerces (l'inverse du garde-fou tenant, cf. app/models/platform.py). Additif et
réversible.

Revision ID: 0023_platform_plane
Revises: 0022_tenant_composite_indexes
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_platform_plane"
down_revision: str | None = "0022_tenant_composite_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cycle de vie du commerce (contrôle d'accès). Défaut 'active' pour l'existant.
    op.add_column(
        "organization",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )

    op.create_table(
        "platform_admin",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="support"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_platform_admin_user"),
    )
    op.create_index("ix_platform_admin_user_id", "platform_admin", ["user_id"])

    op.create_table(
        "subscription",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="trial"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="trialing"),
        sa.Column("mrr_eur", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trial_ends_on", sa.String(length=10), nullable=True),
        sa.Column("started_on", sa.String(length=10), nullable=True),
        sa.Column("current_period_end", sa.String(length=10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", name="uq_subscription_org"),
    )
    op.create_index("ix_subscription_organization_id", "subscription", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_subscription_organization_id", table_name="subscription")
    op.drop_table("subscription")
    op.drop_index("ix_platform_admin_user_id", table_name="platform_admin")
    op.drop_table("platform_admin")
    op.drop_column("organization", "status")
