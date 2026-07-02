"""Registre de modèles MLOps : model_artifact (tenant, versionné).

Revision ID: 0026_model_registry
Revises: 0025_row_level_security
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_model_registry"
down_revision: str | None = "0025_row_level_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_artifact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=True),
        sa.Column("model_name", sa.String(length=32), nullable=False, server_default="naive"),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("baseline", sa.Float(), nullable=False, server_default="0"),
        sa.Column("n_observations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("mape", sa.Float(), nullable=True),
        sa.Column("trigger", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("artifact_uri", sa.String(length=512), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_model_artifact_organization_id", "model_artifact", ["organization_id"])
    op.create_index("ix_model_artifact_product_id", "model_artifact", ["product_id"])
    op.create_index("ix_model_artifact_active", "model_artifact", ["active"])

    # RLS (cohérent avec la migration 0025) : table tenant -> policy tenant_isolation.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        predicate = (
            "current_setting('app.current_org', true) IS NULL "
            "OR current_setting('app.current_org', true) = '' "
            "OR organization_id = current_setting('app.current_org', true)::int"
        )
        op.execute("ALTER TABLE model_artifact ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE model_artifact FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON model_artifact "
            f"USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON model_artifact")
    op.drop_index("ix_model_artifact_active", table_name="model_artifact")
    op.drop_index("ix_model_artifact_product_id", table_name="model_artifact")
    op.drop_index("ix_model_artifact_organization_id", table_name="model_artifact")
    op.drop_table("model_artifact")
