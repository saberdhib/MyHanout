"""Modèle Prophet (stub, dépendance optionnelle).

Installer le groupe `forecasting` (`pip install ".[forecasting]"`) pour activer.
Tombe en erreur explicite si la lib est absente.
"""

from __future__ import annotations

from app.intelligence.forecasting.base import (
    ForecastModel,
    ForecastResult,
    HistoryPoint,
)


class ProphetForecastModel(ForecastModel):
    name = "prophet"

    def predict(
        self,
        history: list[HistoryPoint],
        *,
        horizon_days: int = 14,
        product_id: int | None = None,
    ) -> ForecastResult:
        try:
            from prophet import Prophet  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Prophet non installé. `pip install \".[forecasting]\"` "
                "ou utilisez FORECAST_MODEL=naive."
            ) from exc

        # TODO: construire le DataFrame ds/y, fit + make_future_dataframe + predict,
        # injecter régressseurs (jours fériés, fêtes), mapper vers ForecastResult.
        raise NotImplementedError("Intégration Prophet à implémenter.")
