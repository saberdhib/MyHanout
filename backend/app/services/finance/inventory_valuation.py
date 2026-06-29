"""Valorisation du stock immobilisé (pilotage), avec part périssable à risque.

Valeur = Σ (stock courant × dernier coût d'achat connu via invoice_line). À
défaut de coût d'achat, on retombe sur le prix unitaire catalogue du produit.
La part « à risque » réutilise la détection de péremption (comme les promos).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.stock import Stock
from app.schemas.finance import InventoryItem, InventoryValuation
from app.services.finance.costs import latest_purchase_costs

_AT_RISK_DAYS = 3


async def compute_inventory_value(
    session: AsyncSession, *, at_risk_days: int = _AT_RISK_DAYS
) -> InventoryValuation:
    costs = await latest_purchase_costs(session)
    stocks = list((await session.scalars(select(Stock).options(joinedload(Stock.product)))).all())
    risk_limit = date.today() + timedelta(days=at_risk_days)

    items: list[InventoryItem] = []
    total = 0.0
    at_risk_total = 0.0
    for s in stocks:
        product = s.product
        qty = float(s.quantity or 0)
        unit_cost = costs.get(s.product_id) or float(product.unit_price or 0) if product else 0.0
        value = qty * unit_cost
        total += value
        at_risk = bool(s.expiry_date and s.expiry_date <= risk_limit)
        if at_risk:
            at_risk_total += value
        source = "dernier prix d'achat (facture)" if costs.get(s.product_id) else "prix catalogue"
        items.append(
            InventoryItem(
                product_id=s.product_id,
                product_name=product.name if product else None,
                quantity=qty,
                unit_cost=unit_cost,
                value=value,
                at_risk=at_risk,
                explanation=(
                    f"{qty:g} × {unit_cost:.2f} € ({source})"
                    + (f" — périme le {s.expiry_date} (à risque)" if at_risk else "")
                ),
            )
        )

    items.sort(key=lambda i: i.value, reverse=True)
    return InventoryValuation(
        total_value=total,
        at_risk_value=at_risk_total,
        items=items,
        explanation=(
            f"{len(items)} lot(s) valorisés au dernier coût d'achat connu ; "
            f"{at_risk_total:.0f} € en fin de vie (≤ {at_risk_days} j)."
        ),
    )
