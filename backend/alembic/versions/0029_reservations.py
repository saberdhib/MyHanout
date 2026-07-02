"""Réservations client (click & collect) : reservation + reservation_line (tenant, RLS).

Revision ID: 0029_reservations
Revises: 0028_loyalty
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_reservations"
down_revision: str | None = "0028_loyalty"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RLS = (
    "current_setting('app.current_org', true) IS NULL "
    "OR current_setting('app.current_org', true) = '' "
    "OR organization_id = current_setting('app.current_org', true)::int"
)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON {table} USING ({_RLS}) WITH CHECK ({_RLS})")


def upgrade() -> None:
    op.create_table(
        "reservation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id"), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("pickup_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("loyalty_credited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reservation_organization_id", "reservation", ["organization_id"])
    op.create_index("ix_reservation_customer_id", "reservation", ["customer_id"])
    op.create_index("ix_reservation_status", "reservation", ["status"])

    op.create_table(
        "reservation_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "reservation_id", sa.Integer(), sa.ForeignKey("reservation.id"), nullable=False
        ),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reservation_line_organization_id", "reservation_line", ["organization_id"])
    op.create_index("ix_reservation_line_reservation_id", "reservation_line", ["reservation_id"])
    op.create_index("ix_reservation_line_product_id", "reservation_line", ["product_id"])

    if op.get_bind().dialect.name == "postgresql":
        _enable_rls("reservation")
        _enable_rls("reservation_line")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON reservation_line")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON reservation")
    op.drop_table("reservation_line")
    op.drop_table("reservation")
