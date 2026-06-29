"""Schéma initial MyHanout AI + extension pgvector.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # Extension vectorielle (RAG / recherche sémantique sur documents).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "role",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("permissions", sa.Text),
        *_ts(),
    )
    op.create_index("ix_role_name", "role", ["name"])

    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("phone", sa.String(32)),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("role.id")),
        *_ts(),
    )
    op.create_index("ix_user_email", "user", ["email"])

    op.create_table(
        "supplier",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("address", sa.Text),
        sa.Column("payment_terms_days", sa.Integer, server_default="30"),
        *_ts(),
    )
    op.create_index("ix_supplier_name", "supplier", ["name"])

    op.create_table(
        "product",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(128)),
        sa.Column("unit", sa.String(32), server_default="unit"),
        sa.Column("unit_price", sa.Numeric(10, 2)),
        sa.Column("perishable", sa.Boolean, server_default=sa.false()),
        sa.Column("shelf_life_days", sa.Integer),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("supplier.id")),
        *_ts(),
    )
    op.create_index("ix_product_sku", "product", ["sku"])
    op.create_index("ix_product_name", "product", ["name"])
    op.create_index("ix_product_category", "product", ["category"])

    op.create_table(
        "stock",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="0"),
        sa.Column("location", sa.String(128)),
        sa.Column("reorder_threshold", sa.Numeric(10, 2), server_default="0"),
        sa.Column("expiry_date", sa.Date),
        *_ts(),
    )
    op.create_index("ix_stock_product_id", "stock", ["product_id"])
    op.create_index("ix_stock_expiry_date", "stock", ["expiry_date"])

    op.create_table(
        "sale",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        *_ts(),
    )
    op.create_index("ix_sale_product_id", "sale", ["product_id"])
    op.create_index("ix_sale_sold_at", "sale", ["sold_at"])

    op.create_table(
        "invoice",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("number", sa.String(128)),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("supplier.id")),
        sa.Column("issue_date", sa.Date),
        sa.Column("due_date", sa.Date),
        sa.Column("total_amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), server_default="EUR"),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("ocr_status", sa.String(32), server_default="not_started"),
        sa.Column("source_uri", sa.Text),
        *_ts(),
    )
    op.create_index("ix_invoice_number", "invoice", ["number"])
    op.create_index("ix_invoice_due_date", "invoice", ["due_date"])

    op.create_table(
        "invoice_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer,
            sa.ForeignKey("invoice.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id")),
        sa.Column("description", sa.Text),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="0"),
        sa.Column("unit_price", sa.Numeric(10, 2), server_default="0"),
        sa.Column("line_total", sa.Numeric(12, 2), server_default="0"),
        *_ts(),
    )
    op.create_index("ix_invoice_line_invoice_id", "invoice_line", ["invoice_id"])

    op.create_table(
        "order",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("supplier_id", sa.Integer, sa.ForeignKey("supplier.id")),
        sa.Column("status", sa.String(32), server_default="draft"),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("requires_approval", sa.Boolean, server_default=sa.true()),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("approved_by_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("proposed_by_agent", sa.String(64)),
        *_ts(),
    )

    op.create_table(
        "order_line",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="0"),
        sa.Column("unit_price", sa.Numeric(10, 2), server_default="0"),
        *_ts(),
    )
    op.create_index("ix_order_line_order_id", "order_line", ["order_id"])

    op.create_table(
        "event",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), server_default="info"),
        sa.Column("message", sa.Text),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.Integer),
        sa.Column("payload", sa.Text),
        sa.Column("acknowledged", sa.Boolean, server_default=sa.false()),
        *_ts(),
    )
    op.create_index("ix_event_type", "event", ["type"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource", sa.String(64)),
        sa.Column("resource_id", sa.Integer),
        sa.Column("method", sa.String(8)),
        sa.Column("path", sa.String(255)),
        sa.Column("status_code", sa.Integer),
        sa.Column("detail", sa.Text),
        *_ts(),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])

    # Table de chunks vectorisés pour le RAG documentaire (pgvector).
    # Hors ORM pour ne pas dépendre de pgvector dans les tests sqlite.
    op.execute(
        """
        CREATE TABLE document_chunk (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER REFERENCES invoice(id) ON DELETE CASCADE,
            content TEXT,
            embedding vector(1536),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_chunk")
    op.drop_table("audit_log")
    op.drop_table("event")
    op.drop_table("order_line")
    op.drop_table("order")
    op.drop_table("invoice_line")
    op.drop_table("invoice")
    op.drop_table("sale")
    op.drop_table("stock")
    op.drop_table("product")
    op.drop_table("supplier")
    op.drop_table("user")
    op.drop_table("role")
