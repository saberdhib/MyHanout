"""Service Prix : calcule les prix conseillés, applique une décision (human-in-the-loop)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intelligence.pricing.engine import suggest_price
from app.models.base import PriceKind
from app.models.pricing import PriceHistory
from app.models.product import Product
from app.schemas.pricing import PriceSuggestionOut


async def _unit_cost(session: AsyncSession, product_id: int, current_price: float) -> float:
    row = await session.scalars(
        select(PriceHistory.price)
        .where(PriceHistory.product_id == product_id, PriceHistory.kind == PriceKind.PURCHASE)
        .order_by(PriceHistory.effective_at.desc())
        .limit(1)
    )
    cost = row.first()
    if cost is not None:
        return float(cost)
    return round(current_price * (1.0 - settings.pricing_default_margin_ratio), 2)


async def compute_pricing(
    session: AsyncSession, *, product_ids: list[int] | None = None
) -> list[PriceSuggestionOut]:
    """Prix conseillés (triés par ampleur d'ajustement)."""
    query = select(Product)
    if product_ids:
        query = query.where(Product.id.in_(product_ids))
    products = list((await session.scalars(query)).all())

    out: list[PriceSuggestionOut] = []
    for p in products:
        current = float(p.unit_price or 0.0)
        if current <= 0:
            continue
        cost = await _unit_cost(session, p.id, current)
        decision = suggest_price(product_id=p.id, current_price=current, unit_cost=cost)
        out.append(PriceSuggestionOut(**decision.model_dump(), product_name=p.name))

    out.sort(key=lambda d: abs(d.delta), reverse=True)
    return out


async def apply_price(session: AsyncSession, *, product_id: int, price: float) -> Product | None:
    """Applique un prix de vente (met à jour le produit + trace l'historique)."""
    product = await session.get(Product, product_id)
    if product is None:
        return None
    product.unit_price = price
    session.add(
        PriceHistory(
            product_id=product_id,
            kind=PriceKind.SALE,
            price=price,
            effective_at=datetime.now(UTC),
            source="pricing",
        )
    )
    await session.flush()
    return product
