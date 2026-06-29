"""Marge réelle par produit (pilotage) + détection de dégradation de marge.

Marge unitaire = prix de vente moyen (ventes de la période) − dernier coût
d'achat connu (invoice_line). La dégradation est détectée quand le coût d'achat
le plus récent dépasse le précédent (le fournisseur a augmenté ses prix).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.sale import Sale
from app.schemas.finance import MarginReport, ProductMargin
from app.services.finance.costs import purchase_costs_history


async def compute_margins(
    session: AsyncSession,
    *,
    product_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> MarginReport:
    today = date.today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=90))

    history = await purchase_costs_history(session)

    # Ventes agrégées par produit sur la période.
    stmt = (
        select(
            Sale.product_id,
            func.sum(Sale.total).label("revenue"),
            func.sum(Sale.quantity).label("qty"),
        )
        .where(func.date(Sale.sold_at) >= date_from, func.date(Sale.sold_at) <= date_to)
        .group_by(Sale.product_id)
    )
    if product_id is not None:
        stmt = stmt.where(Sale.product_id == product_id)

    rows = list(await session.execute(stmt))
    product_ids = [r[0] for r in rows]
    names: dict[int, str] = {}
    if product_ids:
        for pid, name in await session.execute(
            select(Product.id, Product.name).where(Product.id.in_(product_ids))
        ):
            names[pid] = name

    items: list[ProductMargin] = []
    for pid, revenue, qty in rows:
        qty = float(qty or 0)
        revenue = float(revenue or 0)
        avg_price = revenue / qty if qty else 0.0
        costs = history.get(pid, [])
        last_cost = costs[0][0] if costs else 0.0
        margin_unit = avg_price - last_cost
        margin_pct = (margin_unit / avg_price) if avg_price else None

        cost_trend = "stable"
        signal = None
        if len(costs) >= 2 and costs[1][0]:
            prev_cost = costs[1][0]
            if last_cost > prev_cost * 1.001:
                cost_trend = "up"
                rise = (last_cost - prev_cost) / prev_cost * 100
                signal = (
                    f"Coût d'achat en hausse de {rise:.0f}% "
                    f"({prev_cost:.2f} → {last_cost:.2f} €) : marge sous pression."
                )
            elif last_cost < prev_cost * 0.999:
                cost_trend = "down"

        items.append(
            ProductMargin(
                product_id=pid,
                product_name=names.get(pid),
                units_sold=qty,
                avg_sale_price=avg_price,
                last_cost=last_cost,
                margin_unit=margin_unit,
                margin_pct=margin_pct,
                cost_trend=cost_trend,
                signal=signal,
                explanation=(
                    f"Prix de vente moyen {avg_price:.2f} € − coût d'achat {last_cost:.2f} € "
                    f"= {margin_unit:.2f} €/unité sur {qty:g} vendues."
                ),
            )
        )

    items.sort(key=lambda i: i.margin_unit)
    return MarginReport(
        period_from=date_from,
        period_to=date_to,
        items=items,
        explanation=(
            f"Marge par produit du {date_from} au {date_to} "
            f"(vente moyenne − dernier coût d'achat). {len(items)} produit(s)."
        ),
    )
