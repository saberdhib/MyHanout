"""Modèle LightGBM (stub, dépendance optionnelle).

Approche par features (lags, rolling, calendrier). Activer via le groupe
`forecasting`. Erreur explicite si la lib est absente.
"""

from __future__ import annotations

from app.intelligence.forecasting.base import (
    ForecastModel,
    ForecastResult,
    HistoryPoint,
)


class LightGBMForecastModel(ForecastModel):
    name = "lgbm"

    def predict(
        self,
        history: list[HistoryPoint],
        *,
        horizon_days: int = 14,
        product_id: int | None = None,
    ) -> ForecastResult:
        try:
            import lightgbm  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                'LightGBM non installé. `pip install ".[forecasting]"` '
                "ou utilisez FORECAST_MODEL=naive."
            ) from exc

        # TODO: feature engineering (lags/rolling/calendrier), train, prévision
        # récursive sur l'horizon, mapping vers ForecastResult.
        raise NotImplementedError("Intégration LightGBM à implémenter.")
