"""Endpoints catalogue (/catalog/*) : familles produit + historique des prix."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.models.base import PRODUCT_FAMILIES, PriceKind
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.catalog import ProductCreate, ProductOut, ProductUpdate
from app.schemas.common import ListResponse
from app.services.price_service import price_history, record_price

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        sku=p.sku,
        name=p.name,
        category=p.category,
        family=p.family,
        unit=p.unit,
        unit_price=float(p.unit_price) if p.unit_price is not None else None,
        perishable=bool(p.perishable),
        shelf_life_days=p.shelf_life_days,
        supplier_id=p.supplier_id,
    )


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


@router.get("/products", response_model=ListResponse[ProductOut])
async def list_products(
    family: str | None = None,
    search: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[ProductOut]:
    """Liste des produits (filtrable par famille / recherche), pour la gestion catalogue."""
    rows = await ProductRepository(session).list_all(family=family, search=search)
    items = [_product_out(p) for p in rows]
    return ListResponse(items=items, total=len(items))


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ProductOut:
    """Crée un produit (rattaché à l'org courante par le garde-fou)."""
    repo = ProductRepository(session)
    if await repo.get_by_sku(body.sku):
        raise HTTPException(status_code=409, detail=f"SKU déjà utilisé : {body.sku}")
    product = Product(**body.model_dump())
    session.add(product)
    await session.flush()
    return _product_out(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ProductOut:
    """Édite un produit (nom, famille, catégorie, prix, péremption…)."""
    product = await session.get(Product, product_id)
    if not product:
        raise NotFoundError(f"Produit {product_id} introuvable")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await session.flush()
    return _product_out(product)


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
