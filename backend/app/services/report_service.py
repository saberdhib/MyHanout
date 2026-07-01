"""Bilan hebdomadaire (agent Bilan) : consolide la semaine écoulée en un rapport
explicable + 3 actions, réutilisant les briques existantes (ventes, marges, alertes,
démarque, réassort). Poussable sur WhatsApp.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.resolver import resolve_whatsapp_client
from app.models.alert import Alert
from app.models.base import AlertStatus, MarkdownStatus, RecommendationStatus
from app.models.markdown import MarkdownSuggestion
from app.models.recommendation import Recommendation
from app.models.sale import Sale
from app.schemas.report import TopProduct, WeeklyReport
from app.services.finance.margin_service import compute_margins


async def _revenue(session: AsyncSession, start: date, end: date) -> tuple[float, float]:
    """(chiffre d'affaires, unités vendues) sur [start, end]."""
    row = (
        await session.execute(
            select(func.sum(Sale.total), func.sum(Sale.quantity)).where(
                func.date(Sale.sold_at) >= start, func.date(Sale.sold_at) <= end
            )
        )
    ).first()
    if row is None:
        return 0.0, 0.0
    return float(row[0] or 0.0), float(row[1] or 0.0)


async def compute_weekly_report(
    session: AsyncSession, *, today: date | None = None
) -> WeeklyReport:
    today = today or date.today()
    start = today - timedelta(days=6)
    prev_start, prev_end = start - timedelta(days=7), start - timedelta(days=1)

    revenue, units = await _revenue(session, start, today)
    revenue_prev, _ = await _revenue(session, prev_start, prev_end)
    delta_pct = round((revenue - revenue_prev) / revenue_prev * 100, 1) if revenue_prev else 0.0

    # Marges (réutilise le service finance) sur la semaine.
    margins = await compute_margins(session, date_from=start, date_to=today)
    gross_margin = round(sum(i.margin_unit * i.units_sold for i in margins.items), 2)
    gross_margin_pct = round(gross_margin / revenue * 100, 1) if revenue else 0.0

    top = sorted(
        (
            TopProduct(
                product_id=i.product_id,
                name=i.product_name,
                revenue=round(i.avg_sale_price * i.units_sold, 2),
            )
            for i in margins.items
        ),
        key=lambda t: t.revenue,
        reverse=True,
    )[:3]

    alerts_open = int(
        (
            await session.execute(
                select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.OPEN)
            )
        ).scalar()
        or 0
    )
    markdown_recovered = float(
        (
            await session.execute(
                select(func.sum(MarkdownSuggestion.recovered_value)).where(
                    MarkdownSuggestion.status == MarkdownStatus.APPLIED
                )
            )
        ).scalar()
        or 0.0
    )
    orders_suggested = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Recommendation)
                .where(
                    Recommendation.status == RecommendationStatus.SUGGESTED,
                    Recommendation.action == "order",
                )
            )
        ).scalar()
        or 0
    )

    # Points saillants (explicables).
    highlights: list[str] = []
    trend = "en hausse" if delta_pct > 0 else ("en baisse" if delta_pct < 0 else "stable")
    highlights.append(
        f"Chiffre d'affaires {revenue:.0f} € ({delta_pct:+.0f}% vs semaine précédente, {trend})."
    )
    highlights.append(f"Marge brute {gross_margin:.0f} € (~{gross_margin_pct:.0f}%).")
    if top:
        highlights.append(f"Meilleure vente : {top[0].name} ({top[0].revenue:.0f} €).")
    if markdown_recovered > 0:
        highlights.append(f"Anti-gaspi : ~{markdown_recovered:.0f} € récupérés via la démarque.")

    # Actions conseillées (posture conseil).
    actions: list[str] = []
    if alerts_open:
        actions.append(f"Traiter {alerts_open} alerte(s) ouverte(s).")
    if orders_suggested:
        actions.append(f"Valider le réassort ({orders_suggested} produit(s) à commander).")
    if gross_margin_pct and gross_margin_pct < 25:
        actions.append("Marge sous 25 % : revoir les prix (agent Prix).")
    if not actions:
        actions.append("Rien d'urgent : continuez sur cette lancée. 👍")

    narrative = (
        f"Semaine du {start.isoformat()} au {today.isoformat()} : "
        f"{revenue:.0f} € de CA ({delta_pct:+.0f}%), marge ~{gross_margin_pct:.0f}%. "
        + (f"{alerts_open} alerte(s) à traiter. " if alerts_open else "")
        + (f"{orders_suggested} réassort à valider." if orders_suggested else "")
    ).strip()

    return WeeklyReport(
        period_start=start.isoformat(),
        period_end=today.isoformat(),
        revenue=round(revenue, 2),
        revenue_prev=round(revenue_prev, 2),
        revenue_delta_pct=delta_pct,
        units_sold=round(units, 2),
        gross_margin=gross_margin,
        gross_margin_pct=gross_margin_pct,
        top_products=top,
        alerts_open=alerts_open,
        markdown_recovered=round(markdown_recovered, 2),
        orders_suggested=orders_suggested,
        highlights=highlights,
        actions=actions,
        narrative=narrative,
    )


def format_report_text(r: WeeklyReport) -> str:
    lines = [
        f"📊 Bilan MyHanout — semaine du {r.period_start}",
        r.narrative,
        "",
        "Points clés :",
        *[f"• {h}" for h in r.highlights],
        "",
        "À faire :",
        *[f"→ {a}" for a in r.actions],
    ]
    return "\n".join(lines)


async def send_weekly_report(session: AsyncSession, *, to: str = "demo") -> WeeklyReport:
    report = await compute_weekly_report(session)
    client = await resolve_whatsapp_client(session)
    await client.send_text(to, format_report_text(report))
    return report
