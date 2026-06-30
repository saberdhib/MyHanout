"""Service de production en magasin : plan (combien fabriquer) + besoins ingrédients.

Pour chaque produit fini ayant une recette active :
- demande prévue (service ML, repli in-process) sur l'horizon,
- stock fini disponible,
- moteur de planification → quantité à produire (arrondi au rendement).

Puis agrégation des **ingrédients consommés** (recette × fournées) et de leur coût.
Human-in-the-loop : plan `suggested` → `confirmed`/`dismissed`.
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.tenancy import get_current_org
from app.intelligence.forecasting.service_client import get_forecast_service_client
from app.intelligence.production.engine import plan_production
from app.models.base import ProductionStatus
from app.models.product import Product
from app.models.recipe import ProductionPlan, Recipe
from app.repositories.sale import SaleRepository
from app.repositories.stock import StockRepository
from app.schemas.recipe import (
    IngredientNeed,
    ProductionPlanOut,
    ProductionPlanResult,
)


async def _names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = await session.execute(select(Product.id, Product.name).where(Product.id.in_(ids)))
    return {r[0]: r[1] for r in rows}


async def _unit_prices(session: AsyncSession, ids: set[int]) -> dict[int, float]:
    if not ids:
        return {}
    rows = await session.execute(select(Product.id, Product.unit_price).where(Product.id.in_(ids)))
    return {pid: float(price or 0.0) for pid, price in rows}


async def compute_production(
    session: AsyncSession,
    *,
    persist: bool = False,
    pipeline_run_id: int | None = None,
    today: date | None = None,
) -> ProductionPlanResult:
    """Calcule le plan de production + les besoins ingrédients (optionnellement persisté)."""
    today = today or date.today()
    horizon = settings.forecast_horizon_days
    stock_repo = StockRepository(session)
    sale_repo = SaleRepository(session)
    client = get_forecast_service_client()

    recipes = list(
        (
            await session.scalars(
                select(Recipe).where(Recipe.active.is_(True)).options(selectinload(Recipe.items))
            )
        ).all()
    )

    if persist:
        # Remplace le jeu "suggested" précédent (DELETE ORM → filtrer l'org À LA MAIN).
        org_id = get_current_org()
        if org_id is not None:
            await session.execute(
                delete(ProductionPlan).where(
                    ProductionPlan.organization_id == org_id,
                    ProductionPlan.status == ProductionStatus.SUGGESTED,
                )
            )

    plans: list[ProductionPlanOut] = []
    ingredient_qty: dict[int, float] = {}
    ingredient_unit: dict[int, str] = {}
    persisted: list[ProductionPlan] = []

    fin_ids = {r.product_id for r in recipes}
    ing_ids = {i.ingredient_product_id for r in recipes for i in r.items}
    names = await _names(session, fin_ids | ing_ids)
    prices = await _unit_prices(session, ing_ids)

    for recipe in recipes:
        fc = await client.predict_product(
            session, recipe.product_id, horizon_days=horizon, model_name=None
        )
        forecast_demand = float(sum(p.yhat for p in fc.points))
        current = await stock_repo.total_quantity(recipe.product_id)
        history = await sale_repo.daily_history(recipe.product_id)

        decision = plan_production(
            product_id=recipe.product_id,
            forecast_demand=forecast_demand,
            current_stock=current,
            yield_quantity=float(recipe.yield_quantity),
            horizon_days=horizon,
            history_days=len(history),
        )

        # Besoins ingrédients = fournées × quantité par fournée.
        for item in recipe.items:
            need = decision.batches * float(item.quantity)
            if need <= 0:
                continue
            ingredient_qty[item.ingredient_product_id] = (
                ingredient_qty.get(item.ingredient_product_id, 0.0) + need
            )
            ingredient_unit.setdefault(item.ingredient_product_id, item.unit)

        if persist:
            row = ProductionPlan(
                product_id=recipe.product_id,
                recipe_id=recipe.id,
                pipeline_run_id=pipeline_run_id,
                model_version=client.model_version(),
                plan_date=today,
                horizon_days=decision.horizon_days,
                forecast_demand=decision.forecast_demand,
                current_stock=decision.current_stock,
                suggested_quantity=decision.suggested_quantity,
                batches=decision.batches,
                confidence=decision.confidence,
                explanation=decision.explanation,
                data_used=json.dumps(decision.data_used, ensure_ascii=False),
            )
            session.add(row)
            persisted.append(row)
        else:
            plans.append(
                ProductionPlanOut(
                    id=0,
                    product_id=recipe.product_id,
                    product_name=names.get(recipe.product_id),
                    recipe_id=recipe.id,
                    plan_date=today.isoformat(),
                    horizon_days=decision.horizon_days,
                    forecast_demand=decision.forecast_demand,
                    current_stock=decision.current_stock,
                    suggested_quantity=decision.suggested_quantity,
                    batches=decision.batches,
                    confidence=decision.confidence,
                    status="suggested",
                    model_version="live",
                    explanation=decision.explanation,
                )
            )

    if persist:
        await session.flush()
        for row in persisted:
            plans.append(
                ProductionPlanOut(
                    id=row.id,
                    product_id=row.product_id,
                    product_name=names.get(row.product_id),
                    recipe_id=row.recipe_id,
                    plan_date=row.plan_date.isoformat() if row.plan_date else None,
                    horizon_days=row.horizon_days,
                    forecast_demand=row.forecast_demand,
                    current_stock=row.current_stock,
                    suggested_quantity=row.suggested_quantity,
                    batches=row.batches,
                    confidence=row.confidence,
                    status=str(row.status),
                    model_version=row.model_version,
                    explanation=row.explanation,
                )
            )

    ingredients = [
        IngredientNeed(
            ingredient_product_id=pid,
            ingredient_name=names.get(pid),
            quantity=round(qty, 3),
            unit=ingredient_unit.get(pid, "unit"),
            estimated_cost=round(qty * prices.get(pid, 0.0), 2),
        )
        for pid, qty in sorted(ingredient_qty.items())
    ]
    total = round(sum(i.estimated_cost for i in ingredients), 2)
    plans.sort(key=lambda p: p.suggested_quantity, reverse=True)
    return ProductionPlanResult(plans=plans, ingredients=ingredients, total_ingredient_cost=total)


async def set_status(
    session: AsyncSession, plan_id: int, status: ProductionStatus
) -> ProductionPlan | None:
    """Confirme/écarte un plan (human-in-the-loop). Le garde-fou filtre l'org."""
    plan = await session.get(ProductionPlan, plan_id)
    if plan is None:
        return None
    plan.status = status
    await session.flush()
    return plan
