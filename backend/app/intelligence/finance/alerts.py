"""Alertes finance explicables (proposées, jamais d'action sortante automatique).

Calées sur la réalité du commerce, toutes tenant-scopées via l'ORM :
- facture en double (même fournisseur + même montant, fenêtre temporelle) ;
- anomalie de prix fournisseur (écart vs achats précédents au-delà d'un seuil) ;
- marge en baisse (coût d'achat qui monte) ;
- échéance proche / risque de trésorerie.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.invoice import Invoice
from app.schemas.finance import FinanceAlert, FinanceAlerts
from app.services.finance.costs import purchase_costs_history
from app.services.finance.margin_service import compute_margins

_DUP_WINDOW_DAYS = 30


async def _duplicate_invoices(session: AsyncSession) -> list[FinanceAlert]:
    """Même fournisseur + même montant à <= 30 j d'écart → doublon probable."""
    rows = list(
        await session.execute(
            select(Invoice.supplier_id, Invoice.total_amount, func.count(Invoice.id))
            .where(Invoice.supplier_id.is_not(None), Invoice.total_amount.is_not(None))
            .group_by(Invoice.supplier_id, Invoice.total_amount)
            .having(func.count(Invoice.id) > 1)
        )
    )
    alerts: list[FinanceAlert] = []
    for supplier_id, amount, _ in rows:
        invs = list(
            (
                await session.scalars(
                    select(Invoice)
                    .where(
                        Invoice.supplier_id == supplier_id,
                        Invoice.total_amount == amount,
                    )
                    .order_by(Invoice.issue_date.asc().nullslast())
                )
            ).all()
        )
        # Fenêtre temporelle : factures datées et rapprochées (<= 30 j) → doublon probable.
        dates: list[date] = [i.issue_date for i in invs if i.issue_date is not None]
        dates.sort()
        close_window = len(dates) >= 2 and (dates[-1] - dates[0]).days <= _DUP_WINDOW_DAYS
        window_note = (
            " (à quelques jours d'écart)" if close_window else " (à vérifier : dates éloignées)"
        )
        alerts.append(
            FinanceAlert(
                type="duplicate_invoice",
                severity="warning",
                title="Facture en double probable",
                reason=(
                    f"{len(invs)} factures du même fournisseur pour un montant identique "
                    f"de {float(amount):.2f} €{window_note}."
                ),
                invoice_ids=[i.id for i in invs],
            )
        )
    return alerts


async def _price_anomalies(session: AsyncSession) -> list[FinanceAlert]:
    threshold = settings.finance_price_anomaly_pct
    alerts: list[FinanceAlert] = []
    for product_id, costs in (await purchase_costs_history(session)).items():
        if len(costs) >= 2 and costs[1][0]:
            last, prev = costs[0][0], costs[1][0]
            if prev and (last - prev) / prev > threshold:
                rise = (last - prev) / prev * 100
                alerts.append(
                    FinanceAlert(
                        type="price_anomaly",
                        severity="warning",
                        title="Anomalie de prix fournisseur",
                        reason=(
                            f"Coût d'achat +{rise:.0f}% ({prev:.2f} → {last:.2f} €) "
                            f"au-delà du seuil de {threshold * 100:.0f}%."
                        ),
                        product_id=product_id,
                    )
                )
    return alerts


async def _margin_drops(session: AsyncSession) -> list[FinanceAlert]:
    report = await compute_margins(session)
    return [
        FinanceAlert(
            type="margin_drop",
            severity="warning",
            title=f"Marge en baisse — {m.product_name or m.product_id}",
            reason=m.signal or "Marge sous pression.",
            product_id=m.product_id,
        )
        for m in report.items
        if m.cost_trend == "up" and m.signal
    ]


async def _due_soon(session: AsyncSession, *, days: int = 7) -> list[FinanceAlert]:
    horizon = date.today() + timedelta(days=days)
    invs = list(
        (
            await session.scalars(
                select(Invoice).where(
                    Invoice.paid.is_(False),
                    Invoice.due_date.is_not(None),
                    Invoice.due_date <= horizon,
                )
            )
        ).all()
    )
    if not invs:
        return []
    total = sum(float(i.total_amount or 0) for i in invs)
    return [
        FinanceAlert(
            type="due_soon",
            severity="info",
            title="Échéances de paiement proches",
            reason=f"{len(invs)} facture(s) à régler sous {days} j, soit {total:.0f} €.",
            invoice_ids=[i.id for i in invs],
        )
    ]


async def compute_finance_alerts(session: AsyncSession) -> FinanceAlerts:
    """Agrège toutes les alertes finance (lecture seule, human-in-the-loop)."""
    alerts: list[FinanceAlert] = []
    alerts += await _duplicate_invoices(session)
    alerts += await _price_anomalies(session)
    alerts += await _margin_drops(session)
    alerts += await _due_soon(session)
    return FinanceAlerts(
        alerts=alerts,
        explanation=(
            "Alertes proposées à partir de vos factures et ventes — aucune action "
            "n'est déclenchée automatiquement."
        ),
    )
