"""Row-Level Security Postgres (defense-in-depth multi-tenant).

Active + FORCE la RLS sur toutes les tables tenant et pose une policy comparant
`organization_id` au GUC de session `app.current_org` (posé par `core/rls.py`).

- GUC = id d'org  → seules ses lignes (SELECT/INSERT/UPDATE/DELETE).
- GUC vide/NULL   → accès complet (plateforme/seed/workers) — miroir du garde-fou
  applicatif `current_org=None`.

`FORCE ROW LEVEL SECURITY` s'applique même au propriétaire des tables (l'app se
connecte en `myhanout`, propriétaire) : sans lui, l'owner contournerait la RLS.

PostgreSQL uniquement (no-op ailleurs : sqlite de test n'a pas de RLS).

Revision ID: 0025_row_level_security
Revises: 0024_support_releases
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025_row_level_security"
down_revision: str | None = "0024_support_releases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables héritant de TenantMixin (colonne organization_id). Tenir à jour si on ajoute
# un modèle tenant (cf. CLAUDE.md §5 + app/models/tenant.py).
_TENANT_TABLES = [
    "agent_memory",
    "alert",
    "api_key",
    "briefing_item",
    "customer",
    "daily_briefing",
    "daily_entry",
    "equipment",
    "expense_classification_feedback",
    "external_signal",
    "forecast_evaluation",
    "hygiene_record",
    "hygiene_task",
    "inventory_snapshot",
    "invoice",
    "markdown_suggestion",
    "meat_cut",
    "meat_lot",
    "order",
    "pipeline_run",
    "price_history",
    "product",
    "production_plan",
    "promo_campaign",
    "recipe",
    "recipe_item",
    "recommendation",
    "sale",
    "stock",
    "supplier",
    "support_message",
    "support_ticket",
    "temperature_reading",
    "tenant_connector",
    "webhook_endpoint",
]

_POLICY = "tenant_isolation"

# GUC vide/NULL = accès complet ; sinon organization_id doit matcher.
_PREDICATE = (
    "current_setting('app.current_org', true) IS NULL "
    "OR current_setting('app.current_org', true) = '' "
    "OR organization_id = current_setting('app.current_org', true)::int"
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # RLS = PostgreSQL uniquement (sqlite de test ignoré)
    for table in _TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY {_POLICY} ON "{table}" '
            f"USING ({_PREDICATE}) WITH CHECK ({_PREDICATE})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TENANT_TABLES:
        op.execute(f'DROP POLICY IF EXISTS {_POLICY} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
