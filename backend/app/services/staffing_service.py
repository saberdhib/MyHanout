"""Service Effectifs : dérive de l'affluence prévue un besoin de personnel par jour.

Approche légère et explicable : on estime la demande par jour de semaine à partir de
l'historique des ventes (total magasin), on projette sur l'horizon, et on convertit
en effectif via une capacité (unités/personne/jour). Pas de données horaires requises.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intelligence.staffing.engine import WEEKDAYS_FR, suggest_staff
from app.models.sale import Sale
from app.schemas.staffing import StaffingDay, StaffingPlan


async def _daily_totals(session: AsyncSession) -> list[tuple[str, float]]:
    """[(jour ISO, quantité totale)] sur tout le magasin (tenant filtré par le garde-fou)."""
    day = func.date(Sale.sold_at)
    rows = await session.execute(
        select(day.label("d"), func.sum(Sale.quantity).label("q")).group_by(day).order_by(day)
    )
    return [(str(r.d), float(r.q)) for r in rows.all()]


def _weekday_averages(totals: list[tuple[str, float]]) -> tuple[dict[int, float], float]:
    """Moyenne de demande par jour de semaine (0=lundi) + moyenne globale."""
    by_wd: dict[int, list[float]] = {}
    for iso, qty in totals:
        try:
            wd = date.fromisoformat(iso).weekday()
        except ValueError:
            continue
        by_wd.setdefault(wd, []).append(qty)
    averages = {wd: sum(v) / len(v) for wd, v in by_wd.items()}
    overall = sum(q for _, q in totals) / len(totals) if totals else 0.0
    return averages, round(overall, 2)


async def compute_staffing(
    session: AsyncSession,
    *,
    horizon_days: int | None = None,
    base_staff: int | None = None,
    units_per_staff: float | None = None,
    today: date | None = None,
) -> StaffingPlan:
    """Plan d'effectifs sur l'horizon (conseil, human-in-the-loop)."""
    horizon = horizon_days or settings.staffing_horizon_days
    base = settings.staffing_base_staff if base_staff is None else base_staff
    cap = settings.staffing_units_per_staff_day if units_per_staff is None else units_per_staff
    today = today or date.today()

    totals = await _daily_totals(session)
    wd_avg, overall = _weekday_averages(totals)

    days: list[StaffingDay] = []
    for i in range(horizon):
        d = today + timedelta(days=i)
        wd = d.weekday()
        predicted = wd_avg.get(wd, overall)
        suggested, delta, vs_avg, explanation = suggest_staff(
            predicted_demand=predicted,
            average_demand=overall,
            units_per_staff_day=cap,
            base_staff=base,
        )
        days.append(
            StaffingDay(
                date=d.isoformat(),
                weekday=WEEKDAYS_FR[wd],
                predicted_demand=round(predicted, 1),
                vs_average_pct=vs_avg,
                suggested_staff=suggested,
                base_staff=base,
                delta=delta,
                explanation=explanation,
            )
        )

    peaks = [d for d in days if d.delta > 0]
    if not totals:
        explanation = "Pas encore assez de ventes pour estimer l'affluence."
    elif peaks:
        explanation = (
            f"{len(peaks)} jour(s) de pic sur {horizon} → renfort conseillé "
            f"(capacité {cap:.0f} unités/personne/jour)."
        )
    else:
        explanation = f"Affluence régulière : l'effectif de base ({base}) couvre l'horizon."

    return StaffingPlan(
        days=days,
        average_demand=overall,
        base_staff=base,
        units_per_staff=cap,
        explanation=explanation,
    )
