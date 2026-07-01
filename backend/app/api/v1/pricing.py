"""Endpoints Prix : suggestions (live) + application d'un prix (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.pricing import PriceApplyRequest, PriceSuggestionOut
from app.services.pricing_service import apply_price, compute_pricing

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/suggestions", response_model=ListResponse[PriceSuggestionOut])
async def suggestions(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("catalog")),
) -> ListResponse[PriceSuggestionOut]:
    """Prix conseillés (marge cible + arrondi psychologique), triés par ajustement."""
    items = await compute_pricing(session)
    return ListResponse(items=items, total=len(items))


@router.post("/apply", response_model=PriceSuggestionOut)
async def apply(
    body: PriceApplyRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("catalog")),
) -> PriceSuggestionOut:
    """Applique un prix de vente (met à jour le produit + trace l'historique)."""
    product = await apply_price(session, product_id=body.product_id, price=body.price)
    if product is None:
        raise NotFoundError("Produit introuvable")
    await session.commit()
    items = await compute_pricing(session, product_ids=[body.product_id])
    if items:
        return items[0]
    # Prix déjà cohérent après application → renvoyer un état neutre.
    raise NotFoundError("Produit introuvable")
