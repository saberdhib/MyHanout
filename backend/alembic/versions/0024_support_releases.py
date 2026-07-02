"""Support & mises à jour : support_ticket, support_message (tenant), release_note (global).

Revision ID: 0024_support_releases
Revises: 0023_platform_plane
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_support_releases"
down_revision: str | None = "0023_platform_plane"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_ticket",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("assigned_admin_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_support_ticket_organization_id", "support_ticket", ["organization_id"])
    op.create_index("ix_support_ticket_status", "support_ticket", ["status"])

    op.create_table(
        "support_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "ticket_id", sa.Integer(), sa.ForeignKey("support_ticket.id"), nullable=False
        ),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("author_kind", sa.String(length=16), nullable=False, server_default="merchant"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_support_message_organization_id", "support_message", ["organization_id"])
    op.create_index("ix_support_message_ticket_id", "support_message", ["ticket_id"])

    op.create_table(
        "release_note",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False, server_default="feature"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_release_note_version", "release_note", ["version"])
    op.create_index("ix_release_note_published", "release_note", ["published"])


def downgrade() -> None:
    op.drop_index("ix_release_note_published", table_name="release_note")
    op.drop_index("ix_release_note_version", table_name="release_note")
    op.drop_table("release_note")
    op.drop_index("ix_support_message_ticket_id", table_name="support_message")
    op.drop_index("ix_support_message_organization_id", table_name="support_message")
    op.drop_table("support_message")
    op.drop_index("ix_support_ticket_status", table_name="support_ticket")
    op.drop_index("ix_support_ticket_organization_id", table_name="support_ticket")
    op.drop_table("support_ticket")
