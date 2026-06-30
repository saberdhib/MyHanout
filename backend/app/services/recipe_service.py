"""Service recettes (nomenclature) : CRUD explicite, tenant-scopé."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.models.recipe import Recipe, RecipeItem
from app.schemas.recipe import RecipeIn, RecipeItemOut, RecipeOut


async def _product_names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = await session.execute(select(Product.id, Product.name).where(Product.id.in_(ids)))
    return {r[0]: r[1] for r in rows}


async def list_recipes(session: AsyncSession) -> list[RecipeOut]:
    recipes = list(
        (await session.scalars(select(Recipe).options(selectinload(Recipe.items)))).all()
    )
    ids: set[int] = set()
    for r in recipes:
        ids.add(r.product_id)
        ids.update(i.ingredient_product_id for i in r.items)
    names = await _product_names(session, ids)
    return [
        RecipeOut(
            id=r.id,
            product_id=r.product_id,
            product_name=names.get(r.product_id),
            name=r.name,
            yield_quantity=float(r.yield_quantity),
            unit=r.unit,
            active=r.active,
            notes=r.notes,
            items=[
                RecipeItemOut(
                    id=i.id,
                    ingredient_product_id=i.ingredient_product_id,
                    ingredient_name=names.get(i.ingredient_product_id),
                    quantity=float(i.quantity),
                    unit=i.unit,
                )
                for i in r.items
            ],
        )
        for r in recipes
    ]


async def create_recipe(session: AsyncSession, data: RecipeIn) -> int:
    recipe = Recipe(
        product_id=data.product_id,
        name=data.name,
        yield_quantity=data.yield_quantity,
        unit=data.unit,
        notes=data.notes,
    )
    for it in data.items:
        recipe.items.append(
            RecipeItem(
                ingredient_product_id=it.ingredient_product_id,
                quantity=it.quantity,
                unit=it.unit,
            )
        )
    session.add(recipe)
    await session.flush()
    return recipe.id


async def delete_recipe(session: AsyncSession, recipe_id: int) -> bool:
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        return False
    await session.delete(recipe)
    await session.flush()
    return True
