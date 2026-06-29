"""Multi-tenant : organization + membership + invitation, organization_id partout.

Revision ID: 0003_multitenant
Revises: 0002_invoice_review
Create Date: 2026-06-29

Backfill : les enregistrements existants (seeds) sont rattachés à une organisation
par défaut (« demo »), puis organization_id passe NOT NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_multitenant"
down_revision: str | None = "0002_invoice_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_TABLES = ["product", "stock", "sale", "supplier", "invoice", "order"]


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("business_type", sa.String(64)),
        *_ts(),
    )
    op.create_index("ix_organization_slug", "organization", ["slug"])
    op.create_index("ix_organization_name", "organization", ["name"])

    op.create_table(
        "membership",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("role", sa.String(32), server_default="staff"),
        *_ts(),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )
    op.create_index("ix_membership_user_id", "membership", ["user_id"])
    op.create_index("ix_membership_organization_id", "membership", ["organization_id"])

    op.create_table(
        "invitation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), server_default="staff"),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("accepted", sa.Boolean, server_default=sa.false()),
        sa.Column("invited_by_id", sa.Integer, sa.ForeignKey("user.id")),
        *_ts(),
    )
    op.create_index("ix_invitation_token", "invitation", ["token"])
    op.create_index("ix_invitation_email", "invitation", ["email"])
    op.create_index("ix_invitation_organization_id", "invitation", ["organization_id"])

    # Organisation par défaut pour rattacher les données existantes.
    op.execute(
        "INSERT INTO organization (name, slug, created_at, updated_at) "
        "VALUES ('Commerce Démo', 'demo', now(), now())"
    )

    for table in _TENANT_TABLES:
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
        op.execute(
            f'UPDATE "{table}" SET organization_id = '
            "(SELECT id FROM organization WHERE slug='demo')"
        )
        op.alter_column(table, "organization_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_organization", table, "organization", ["organization_id"], ["id"]
        )
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])


def downgrade() -> None:
    for table in _TENANT_TABLES:
        op.drop_index(f"ix_{table}_organization_id", table)
        op.drop_constraint(f"fk_{table}_organization", table, type_="foreignkey")
        op.drop_column(table, "organization_id")
    op.drop_table("invitation")
    op.drop_table("membership")
    op.drop_table("organization")
