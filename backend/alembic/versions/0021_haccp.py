"""Carnet HACCP : hygiene_task (plan de nettoyage) + hygiene_record (traçabilité).

Tables tenant. Réversible.

Revision ID: 0021_haccp
Revises: 0020_tenant_connectors
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_haccp"
down_revision: str | None = "0020_tenant_connectors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "hygiene_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False, server_default="daily"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_hygiene_task_organization_id", "hygiene_task", ["organization_id"])
    op.create_index("ix_hygiene_task_frequency", "hygiene_task", ["frequency"])

    op.create_table(
        "hygiene_record",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("hygiene_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("done_by", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_hygiene_record_organization_id", "hygiene_record", ["organization_id"])
    op.create_index("ix_hygiene_record_task_id", "hygiene_record", ["task_id"])
    op.create_index("ix_hygiene_record_done_at", "hygiene_record", ["done_at"])


def downgrade() -> None:
    op.drop_table("hygiene_record")
    op.drop_index("ix_hygiene_task_frequency", table_name="hygiene_task")
    op.drop_index("ix_hygiene_task_organization_id", table_name="hygiene_task")
    op.drop_table("hygiene_task")
