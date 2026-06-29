"""Modèle de prévision naïf — implémentation par défaut, sans dépendance lourde.

Combine une moyenne mobile récente avec les features de saisonnalité, jours
fériés et fêtes. Suffisant pour valider le pipeline bout-en-bout sur les seeds.
"""

from __future__ import annotations

from datetime import timedelta

from app.intelligence.forecasting.base import (
    ForecastModel,
    ForecastPoint,
    ForecastResult,
    HistoryPoint,
)
from app.intelligence.forecasting.features import (
    festival_factor,
    is_holiday,
    weekday_factor,
)


class NaiveForecastModel(ForecastModel):
    name = "naive"

    def __init__(self, window: int = 28) -> None:
        # Fenêtre (jours) pour la moyenne mobile de base.
        self.window = window

    def predict(
        self,
        history: list[HistoryPoint],
        *,
        horizon_days: int = 14,
        product_id: int | None = None,
    ) -> ForecastResult:
        points: list[ForecastPoint] = []
        if not history:
            return ForecastResult(
                product_id=product_id,
                model=self.name,
                horizon_days=horizon_days,
                points=points,
                explanation="Aucun historique : prévision nulle.",
            )

        history = sorted(history, key=lambda p: p.ds)
        recent = history[-self.window :]
        baseline = sum(p.y for p in recent) / len(recent)
        last_date = history[-1].ds

        for i in range(1, horizon_days + 1):
            day = last_date + timedelta(days=i)
            # Jour férié : commerce fermé (hypothèse simplificatrice) -> 0.
            yhat = 0.0 if is_holiday(day) else baseline * weekday_factor(day) * festival_factor(day)
            points.append(
                ForecastPoint(
                    ds=day,
                    yhat=round(yhat, 2),
                    yhat_lower=round(yhat * 0.8, 2),
                    yhat_upper=round(yhat * 1.2, 2),
                )
            )

        explanation = (
            f"Moyenne mobile {len(recent)}j (base={baseline:.1f}) "
            f"ajustée par saisonnalité hebdo, jours fériés et fêtes."
        )
        return ForecastResult(
            product_id=product_id,
            model=self.name,
            horizon_days=horizon_days,
            points=points,
            explanation=explanation,
        )
