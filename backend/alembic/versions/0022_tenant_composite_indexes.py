"""Index composites (organization_id, colonne chaude) — perf multi-tenant.

Le garde-fou filtre par organization_id sur CHAQUE requête ORM ; mettre org_id en
tête d'index accélère les requêtes fréquentes sur les tables volumineuses. Additif
et réversible (aucun changement de schéma logique).

Revision ID: 0022_tenant_composite_indexes
Revises: 0021_haccp
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022_tenant_composite_indexes"
down_revision: str | None = "0021_haccp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (nom_index, table, colonnes)
_INDEXES = [
    ("ix_sale_org_sold_at", "sale", ["organization_id", "sold_at"]),
    ("ix_sale_org_product", "sale", ["organization_id", "product_id"]),
    ("ix_stock_org_product", "stock", ["organization_id", "product_id"]),
    ("ix_invoice_org_status", "invoice", ["organization_id", "status"]),
    ("ix_temp_reading_org_recorded", "temperature_reading", ["organization_id", "recorded_at"]),
    ("ix_recommendation_org_status", "recommendation", ["organization_id", "status"]),
    ("ix_markdown_org_status", "markdown_suggestion", ["organization_id", "status"]),
]


def upgrade() -> None:
    for name, table, cols in _INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _cols in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
