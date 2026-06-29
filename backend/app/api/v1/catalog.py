"""Endpoints catalogue (/catalog/*) : familles produit + historique des prix."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.models.base import PRODUCT_FAMILIES, PriceKind
from app.models.product import Product
from app.services.price_service import price_history, record_price

router = APIRouter(prefix="/catalog", tags=["catalog"])


class PricePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    price: float
    currency: str
    effective_at: datetime
    source: str


class RecordPriceRequest(BaseModel):
    kind: str = "sale"  # sale | purchase
    price: float


@router.get("/families", response_model=list[str])
async def families(
    _: CurrentUser = Depends(require_permission("stocks")),
) -> list[str]:
    """Familles produit suggérées (notion de regroupement, texte libre)."""
    return PRODUCT_FAMILIES


@router.get("/products/{product_id}/prices", response_model=list[PricePoint])
async def get_prices(
    product_id: int,
    kind: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> list[PricePoint]:
    """Historique des prix (achat/vente) d'un produit — courbe d'évolution."""
    pk = PriceKind(kind) if kind else None
    rows = await price_history(session, product_id=product_id, kind=pk)
    return [PricePoint.model_validate(r) for r in rows]


@router.post("/products/{product_id}/prices", response_model=PricePoint)
async def add_price(
    product_id: int,
    body: RecordPriceRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> PricePoint:
    """Enregistre un point de prix (manuel)."""
    product = await session.get(Product, product_id)
    if not product:
        raise NotFoundError(f"Produit {product_id} introuvable")
    entry = await record_price(
        session, product_id=product_id, kind=PriceKind(body.kind), price=body.price, source="manual"
    )
    return PricePoint.model_validate(entry)
