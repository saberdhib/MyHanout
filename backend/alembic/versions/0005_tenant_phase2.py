"""Consolidation : organization_id sur les tables Phase 2 (tenant).

Revision ID: 0005_tenant_phase2
Revises: 0004_conversation
Create Date: 2026-06-29

Rattache daily_entry / forecast_evaluation (tenant strict) et conversation
(routage, nullable) à une organisation. Backfill vers l'org 'default'.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tenant_phase2"
down_revision: str | None = "0004_conversation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STRICT = ["daily_entry", "forecast_evaluation"]


def upgrade() -> None:
    # Tables tenant strictes : backfill vers 'default' puis NOT NULL.
    for table in _STRICT:
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
        op.execute(
            f'UPDATE "{table}" SET organization_id = '
            "(SELECT id FROM organization WHERE slug='default')"
        )
        op.alter_column(table, "organization_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_organization", table, "organization", ["organization_id"], ["id"]
        )
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])

    # Conversation : table de routage, organization_id nullable (résolu au runtime).
    op.add_column("conversation", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_conversation_organization", "conversation", "organization", ["organization_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversation_organization", "conversation", type_="foreignkey")
    op.drop_column("conversation", "organization_id")
    for table in _STRICT:
        op.drop_index(f"ix_{table}_organization_id", table)
        op.drop_constraint(f"fk_{table}_organization", table, type_="foreignkey")
        op.drop_column(table, "organization_id")
