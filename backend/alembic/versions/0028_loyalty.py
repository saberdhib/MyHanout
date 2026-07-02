"""Fidélité client : loyalty_account + loyalty_transaction (tenant, RLS incluse).

Revision ID: 0028_loyalty
Revises: 0027_webhook_inbound
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_loyalty"
down_revision: str | None = "0027_webhook_inbound"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RLS_PREDICATE = (
    "current_setting('app.current_org', true) IS NULL "
    "OR current_setting('app.current_org', true) = '' "
    "OR organization_id = current_setting('app.current_org', true)::int"
)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING ({_RLS_PREDICATE}) WITH CHECK ({_RLS_PREDICATE})"
    )


def upgrade() -> None:
    op.create_table(
        "loyalty_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("customer_id", name="uq_loyalty_account_customer"),
    )
    op.create_index("ix_loyalty_account_organization_id", "loyalty_account", ["organization_id"])
    op.create_index("ix_loyalty_account_customer_id", "loyalty_account", ["customer_id"])

    op.create_table(
        "loyalty_transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "account_id", sa.Integer(), sa.ForeignKey("loyalty_account.id"), nullable=False
        ),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customer.id"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_loyalty_transaction_organization_id", "loyalty_transaction", ["organization_id"]
    )
    op.create_index("ix_loyalty_transaction_account_id", "loyalty_transaction", ["account_id"])
    op.create_index("ix_loyalty_transaction_customer_id", "loyalty_transaction", ["customer_id"])
    op.create_index("ix_loyalty_transaction_kind", "loyalty_transaction", ["kind"])

    if op.get_bind().dialect.name == "postgresql":
        _enable_rls("loyalty_account")
        _enable_rls("loyalty_transaction")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON loyalty_transaction")
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON loyalty_account")
    op.drop_table("loyalty_transaction")
    op.drop_table("loyalty_account")
