"""Production en magasin : recettes (nomenclature) + plans de production.

Tables tenant : recipe (produit fini + rendement), recipe_item (ingrédients),
production_plan (suggestion explicable, human-in-the-loop). Réversible.

Revision ID: 0018_recipes_production
Revises: 0017_markdown
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_recipes_production"
down_revision: str | None = "0017_markdown"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts(col: str):
    return sa.Column(col, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "recipe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("yield_quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="unit"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_recipe_organization_id", "recipe", ["organization_id"])
    op.create_index("ix_recipe_product_id", "recipe", ["product_id"])

    op.create_table(
        "recipe_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipe.id"), nullable=False),
        sa.Column(
            "ingredient_product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False
        ),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="unit"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_recipe_item_organization_id", "recipe_item", ["organization_id"])
    op.create_index("ix_recipe_item_recipe_id", "recipe_item", ["recipe_id"])
    op.create_index(
        "ix_recipe_item_ingredient_product_id", "recipe_item", ["ingredient_product_id"]
    )

    op.create_table(
        "production_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id"), nullable=False),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipe.id"), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_run.id"), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("plan_date", sa.Date(), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("forecast_demand", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Float(), nullable=False, server_default="0"),
        sa.Column("suggested_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("batches", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="suggested"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("data_used", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_production_plan_organization_id", "production_plan", ["organization_id"])
    op.create_index("ix_production_plan_product_id", "production_plan", ["product_id"])
    op.create_index("ix_production_plan_recipe_id", "production_plan", ["recipe_id"])
    op.create_index(
        "ix_production_plan_pipeline_run_id", "production_plan", ["pipeline_run_id"]
    )
    op.create_index("ix_production_plan_plan_date", "production_plan", ["plan_date"])
    op.create_index("ix_production_plan_status", "production_plan", ["status"])


def downgrade() -> None:
    op.drop_table("production_plan")
    op.drop_index("ix_recipe_item_ingredient_product_id", table_name="recipe_item")
    op.drop_index("ix_recipe_item_recipe_id", table_name="recipe_item")
    op.drop_index("ix_recipe_item_organization_id", table_name="recipe_item")
    op.drop_table("recipe_item")
    op.drop_index("ix_recipe_product_id", table_name="recipe")
    op.drop_index("ix_recipe_organization_id", table_name="recipe")
    op.drop_table("recipe")
