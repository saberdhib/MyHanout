"""Interface commune des modèles de prévision de demande."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field


class HistoryPoint(BaseModel):
    """Point d'historique de ventes (agrégation journalière)."""

    ds: date
    y: float


class ForecastPoint(BaseModel):
    """Point de prévision avec intervalle optionnel."""

    ds: date
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None


class ForecastResult(BaseModel):
    product_id: int | None = None
    model: str
    horizon_days: int
    points: list[ForecastPoint] = Field(default_factory=list)
    # Explicabilité : facteurs ayant influé sur la prévision.
    explanation: str | None = None


class ForecastModel(ABC):
    """Contrat commun (naive / Prophet / LightGBM)."""

    name: str = "abstract"

    @abstractmethod
    def predict(
        self,
        history: list[HistoryPoint],
        *,
        horizon_days: int = 14,
        product_id: int | None = None,
    ) -> ForecastResult:
        """Produit une prévision sur `horizon_days` à partir de l'historique."""
        raise NotImplementedError
