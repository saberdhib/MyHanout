"""Vue de trésorerie (pilotage) — lecture seule, dérivée des données existantes.

Ce n'est PAS de la comptabilité certifiée : on estime les flux à partir des
ventes (entrées) et des factures payées / à payer (sorties). Tout est filtré
par tenant via l'ORM (garde-fou central). Chaque chiffre porte une explication.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.sale import Sale
from app.schemas.finance import TreasuryLine, TreasuryView


async def _sum(session: AsyncSession, stmt) -> float:
    return float(await session.scalar(stmt) or 0)


async def compute_treasury(
    session: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> TreasuryView:
    today = date.today()
    date_to = date_to or today
    date_from = date_from or (date_to - timedelta(days=30))

    # Entrées : ventes sur la période.
    sales_in = await _sum(
        session,
        select(func.coalesce(func.sum(Sale.total), 0)).where(
            func.date(Sale.sold_at) >= date_from, func.date(Sale.sold_at) <= date_to
        ),
    )

    # Sorties réalisées : factures payées sur la période (à défaut de paid_at, toutes payées).
    outflows_paid = await _sum(
        session,
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.paid.is_(True)),
    )

    # Sorties à venir : factures non payées avec échéance dans 7 / 30 jours.
    async def upcoming(days: int) -> float:
        horizon = today + timedelta(days=days)
        return await _sum(
            session,
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.paid.is_(False),
                Invoice.due_date.is_not(None),
                Invoice.due_date <= horizon,
            ),
        )

    upcoming_7d = await upcoming(7)
    upcoming_30d = await upcoming(30)

    estimated_balance = sales_in - outflows_paid
    projected_30d = estimated_balance - upcoming_30d

    alert = None
    if projected_30d < 0:
        alert = (
            f"Trésorerie projetée négative à 30 j ({projected_30d:.0f} €) : "
            f"{upcoming_30d:.0f} € de factures à régler face à {estimated_balance:.0f} € estimés."
        )

    lines = [
        TreasuryLine(
            label="Entrées (ventes)",
            amount=sales_in,
            explanation=f"Somme des ventes du {date_from} au {date_to}.",
        ),
        TreasuryLine(
            label="Sorties réalisées (factures payées)",
            amount=-outflows_paid,
            explanation="Total des factures marquées payées.",
        ),
        TreasuryLine(
            label="À payer sous 7 j",
            amount=-upcoming_7d,
            explanation="Factures non payées dont l'échéance tombe dans 7 jours.",
        ),
        TreasuryLine(
            label="À payer sous 30 j",
            amount=-upcoming_30d,
            explanation="Factures non payées dont l'échéance tombe dans 30 jours.",
        ),
    ]

    return TreasuryView(
        period_from=date_from,
        period_to=date_to,
        sales_in=sales_in,
        outflows_paid=outflows_paid,
        estimated_balance=estimated_balance,
        upcoming_7d=upcoming_7d,
        upcoming_30d=upcoming_30d,
        alert=alert,
        lines=lines,
    )
