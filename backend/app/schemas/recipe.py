"""Schémas Pydantic des recettes (nomenclature) et de la production en magasin."""

from __future__ import annotations

from pydantic import BaseModel


# --- Recettes (nomenclature / BOM) ---
class RecipeItemIn(BaseModel):
    ingredient_product_id: int
    quantity: float
    unit: str = "unit"


class RecipeItemOut(BaseModel):
    id: int
    ingredient_product_id: int
    ingredient_name: str | None = None
    quantity: float
    unit: str


class RecipeIn(BaseModel):
    product_id: int
    name: str
    yield_quantity: float = 1
    unit: str = "unit"
    notes: str | None = None
    items: list[RecipeItemIn] = []


class RecipeOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    name: str
    yield_quantity: float
    unit: str
    active: bool
    notes: str | None = None
    items: list[RecipeItemOut] = []


# --- Production (plan + besoins ingrédients) ---
class ProductionDecision(BaseModel):
    """Décision produite par le moteur de production (pure, testable, explicable)."""

    product_id: int
    forecast_demand: float
    current_stock: float
    net_need: float
    batches: float
    suggested_quantity: float
    horizon_days: int
    confidence: float
    explanation: str
    reasons: list[str] = []
    data_used: dict = {}


class ProductionPlanOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    recipe_id: int | None = None
    plan_date: str | None = None
    horizon_days: int
    forecast_demand: float
    current_stock: float
    suggested_quantity: float
    batches: float
    confidence: float
    status: str
    model_version: str
    explanation: str


class IngredientNeed(BaseModel):
    """Besoin agrégé en ingrédient pour réaliser le plan de production."""

    ingredient_product_id: int
    ingredient_name: str | None = None
    quantity: float
    unit: str
    estimated_cost: float


class ProductionPlanResult(BaseModel):
    """Plan de production complet : produits à fabriquer + ingrédients à prévoir."""

    plans: list[ProductionPlanOut] = []
    ingredients: list[IngredientNeed] = []
    total_ingredient_cost: float = 0.0
