"""Coûts d'achat par produit, dérivés des lignes de facture (tenant-scopé).

La jointure passe par `invoice` (qui hérite de `TenantMixin`) : le garde-fou
central filtre donc automatiquement par organisation. Aucun SQL brut.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceLine


async def purchase_costs_history(
    session: AsyncSession,
) -> dict[int, list[tuple[float, date | None]]]:
    """Historique des coûts d'achat par produit, du plus récent au plus ancien."""
    stmt = (
        select(InvoiceLine.product_id, InvoiceLine.unit_price, Invoice.issue_date)
        .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
        .where(InvoiceLine.product_id.is_not(None))
        .order_by(Invoice.issue_date.desc().nullslast(), Invoice.id.desc())
    )
    history: dict[int, list[tuple[float, date | None]]] = {}
    for product_id, unit_price, issued in await session.execute(stmt):
        history.setdefault(product_id, []).append((float(unit_price or 0), issued))
    return history


async def latest_purchase_costs(session: AsyncSession) -> dict[int, float]:
    """Dernier coût d'achat connu par produit (0 si aucune ligne de facture)."""
    return {pid: rows[0][0] for pid, rows in (await purchase_costs_history(session)).items()}
