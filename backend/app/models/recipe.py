"""Recettes (nomenclature / BOM) et plans de production en magasin.

Pour les commerces qui **fabriquent** (boulangerie, traiteur, boucherie-prep) :
une `Recipe` décrit comment produire un produit fini (rendement + ingrédients),
et un `ProductionPlan` propose combien produire (dérivé de la prévision) — avec
le décompte des ingrédients consommés et leur coût.

Human-in-the-loop : plan `suggested` → action humaine → `confirmed`/`dismissed`.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import ProductionStatus
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    pass


class Recipe(Base, TenantMixin, TimestampMixin):
    """Nomenclature d'un produit fini fabriqué en magasin."""

    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Produit fini fabriqué (référence le catalogue).
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    # Rendement : nombre d'unités de produit fini par « fournée »/batch.
    yield_quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    unit: Mapped[str] = mapped_column(String(32), default="unit")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[RecipeItem]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeItem(Base, TenantMixin, TimestampMixin):
    """Un ingrédient d'une recette (quantité consommée par fournée)."""

    __tablename__ = "recipe_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), index=True)
    # Ingrédient = produit du catalogue (farine, levure…).
    ingredient_product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), default=0)
    unit: Mapped[str] = mapped_column(String(32), default="unit")

    recipe: Mapped[Recipe] = relationship(back_populates="items")


class ProductionPlan(Base, TenantMixin, TimestampMixin):
    """Plan de production proposé pour un produit fini, explicable et traçable."""

    __tablename__ = "production_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    recipe_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipe.id"), nullable=True, index=True
    )
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_run.id"), nullable=True, index=True
    )
    model_version: Mapped[str] = mapped_column(String(64), default="v1")

    plan_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    horizon_days: Mapped[int] = mapped_column(default=1)
    forecast_demand: Mapped[float] = mapped_column(Float, default=0.0)
    current_stock: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    batches: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[ProductionStatus] = mapped_column(
        Enum(
            ProductionStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ProductionStatus.SUGGESTED,
        index=True,
    )
    explanation: Mapped[str] = mapped_column(Text)
    data_used: Mapped[str | None] = mapped_column(Text, nullable=True)
