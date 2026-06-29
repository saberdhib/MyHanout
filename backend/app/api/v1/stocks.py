"""Endpoints stocks (lecture)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.repositories.stock import StockRepository
from app.schemas.common import ListResponse
from app.schemas.stock import StockWithProduct

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _to_schema(stock) -> StockWithProduct:
    product = stock.product
    return StockWithProduct(
        id=stock.id,
        product_id=stock.product_id,
        quantity=float(stock.quantity),
        location=stock.location,
        reorder_threshold=float(stock.reorder_threshold),
        expiry_date=stock.expiry_date,
        product_name=product.name if product else None,
        product_sku=product.sku if product else None,
        low_stock=float(stock.quantity) <= float(stock.reorder_threshold),
    )


@router.get("", response_model=ListResponse[StockWithProduct])
async def list_stocks(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("stocks")),
) -> ListResponse[StockWithProduct]:
    repo = StockRepository(session)
    stocks = await repo.list_with_product()
    items = [_to_schema(s) for s in stocks]
    return ListResponse(items=items, total=len(items))


@router.get("/alerts", response_model=ListResponse[StockWithProduct])
async def stock_alerts(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("stocks")),
) -> ListResponse[StockWithProduct]:
    """Stocks en rupture (sous le seuil de réassort)."""
    repo = StockRepository(session)
    low = await repo.list_low_stock()
    items = [_to_schema(s) for s in low]
    return ListResponse(items=items, total=len(items))
