"""Endpoints recettes (nomenclature) : liste, création, suppression."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.recipe import RecipeIn, RecipeOut
from app.services.recipe_service import create_recipe, delete_recipe, list_recipes

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=ListResponse[RecipeOut])
async def get_recipes(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("catalog")),
) -> ListResponse[RecipeOut]:
    """Recettes (produit fini + ingrédients) du commerce."""
    items = await list_recipes(session)
    return ListResponse(items=items, total=len(items))


@router.post("", response_model=RecipeOut, status_code=201)
async def post_recipe(
    body: RecipeIn,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("catalog")),
) -> RecipeOut:
    """Crée une recette (nomenclature) pour un produit fini."""
    rid = await create_recipe(session, body)
    await session.commit()
    items = await list_recipes(session)
    created = next((r for r in items if r.id == rid), None)
    if created is None:
        raise NotFoundError("Recette introuvable après création")
    return created


@router.delete("/{recipe_id}", status_code=204)
async def remove_recipe(
    recipe_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("catalog")),
) -> None:
    """Supprime une recette."""
    ok = await delete_recipe(session, recipe_id)
    if not ok:
        raise NotFoundError("Recette introuvable")
    await session.commit()
