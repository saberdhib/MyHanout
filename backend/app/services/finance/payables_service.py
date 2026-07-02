"""Échéancier fournisseurs + trésorerie prévisionnelle (pilotage, lecture seule).

Regroupe les factures **non payées** par horizon d'échéance (en retard / 7 j / 30 j /
au-delà) et projette la trésorerie semaine par semaine : entrées estimées (moyenne des
ventes) − sorties dues. Ce n'est PAS de la compta certifiée ; chaque chiffre est expliqué.
Filtré par tenant (garde-fou ORM).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.sale import Sale
from app.models.supplier import Supplier
from app.schemas.finance import (
    CashWeek,
    PayableBucket,
    PayableInvoice,
    PayablesView,
)

_WEEKS_AHEAD = 4


async def _avg_daily_sales(session: AsyncSession, days: int = 30) -> float:
    since = date.today() - timedelta(days=days)
    total = float(
        await session.scalar(
            select(func.coalesce(func.sum(Sale.total), 0)).where(func.date(Sale.sold_at) >= since)
        )
        or 0
    )
    return total / days if days else 0.0


async def compute_payables(session: AsyncSession) -> PayablesView:
    today = date.today()

    # Factures non payées (avec ou sans échéance).
    invoices = list(await session.scalars(select(Invoice).where(Invoice.paid.is_(False))))
    suppliers = {s.id: s.name for s in await session.scalars(select(Supplier))}

    bucket_defs = [
        ("overdue", "En retard"),
        ("d7", "Sous 7 jours"),
        ("d30", "Sous 30 jours"),
        ("later", "Au-delà de 30 jours"),
        ("no_date", "Sans échéance"),
    ]
    grouped: dict[str, list[PayableInvoice]] = {k: [] for k, _ in bucket_defs}

    total_due = 0.0
    overdue_amount = 0.0
    for inv in invoices:
        amount = float(inv.total_amount or 0)
        total_due += amount
        if inv.due_date is None:
            key = "no_date"
            days_to = None
            overdue = False
        else:
            days_to = (inv.due_date - today).days
            overdue = days_to < 0
            if overdue:
                key = "overdue"
                overdue_amount += amount
            elif days_to <= 7:
                key = "d7"
            elif days_to <= 30:
                key = "d30"
            else:
                key = "later"
        grouped[key].append(
            PayableInvoice(
                invoice_id=inv.id,
                number=inv.number,
                supplier_name=suppliers.get(inv.supplier_id) if inv.supplier_id else None,
                due_date=inv.due_date.isoformat() if inv.due_date else None,
                amount=amount,
                days_to_due=days_to,
                overdue=overdue,
            )
        )

    buckets = [
        PayableBucket(
            key=k,
            label=label,
            count=len(grouped[k]),
            amount=round(sum(i.amount for i in grouped[k]), 2),
            invoices=sorted(grouped[k], key=lambda i: (i.days_to_due is None, i.days_to_due or 0)),
        )
        for k, label in bucket_defs
        if grouped[k]
    ]

    # Projection hebdomadaire : entrées estimées − sorties dues, solde courant.
    daily = await _avg_daily_sales(session)
    weekly_inflow = round(daily * 7, 2)
    # Solde d'ouverture : ventes 30 j − factures déjà payées (même base que la trésorerie).
    sales_30 = float(
        await session.scalar(
            select(func.coalesce(func.sum(Sale.total), 0)).where(
                func.date(Sale.sold_at) >= today - timedelta(days=30)
            )
        )
        or 0
    )
    paid_out = float(
        await session.scalar(
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.paid.is_(True))
        )
        or 0
    )
    opening = round(sales_30 - paid_out, 2)

    weeks: list[CashWeek] = []
    running = opening
    # Lundi de la semaine courante.
    monday = today - timedelta(days=today.weekday())
    for w in range(_WEEKS_AHEAD):
        start = monday + timedelta(weeks=w)
        end = start + timedelta(days=6)
        due = round(
            sum(
                float(inv.total_amount or 0)
                for inv in invoices
                if inv.due_date is not None and start <= inv.due_date <= end
            ),
            2,
        )
        # Les échéances déjà en retard pèsent sur la première semaine.
        if w == 0:
            due += round(
                sum(
                    float(inv.total_amount or 0)
                    for inv in invoices
                    if inv.due_date is not None and inv.due_date < start
                ),
                2,
            )
        net = round(weekly_inflow - due, 2)
        running = round(running + net, 2)
        weeks.append(
            CashWeek(
                week_start=start.isoformat(),
                expected_inflow=weekly_inflow,
                payables_due=due,
                net=net,
                running_balance=running,
                explanation=(
                    f"Semaine du {start}: ~{weekly_inflow:.0f} € de ventes estimées − "
                    f"{due:.0f} € d'échéances = {net:+.0f} € (solde {running:.0f} €)."
                ),
            )
        )

    low = min((wk.running_balance for wk in weeks), default=opening)
    alert = None
    if low < 0:
        alert = (
            f"Trésorerie projetée négative ({low:.0f} €) sous {_WEEKS_AHEAD} semaines : "
            f"{overdue_amount:.0f} € en retard, {total_due:.0f} € dus au total."
        )

    return PayablesView(
        total_due=round(total_due, 2),
        overdue_amount=round(overdue_amount, 2),
        opening_balance=opening,
        buckets=buckets,
        weeks=weeks,
        alert=alert,
        explanation=(
            f"{len(invoices)} facture(s) à payer ({total_due:.0f} €), dont "
            f"{overdue_amount:.0f} € en retard. Entrées estimées ~{weekly_inflow:.0f} €/semaine."
        ),
        disclaimer=(
            "Estimation de pilotage (non comptable) : entrées projetées d'après les ventes."
        ),
    )
