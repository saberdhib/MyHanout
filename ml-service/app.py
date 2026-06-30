"""Service ML isolé (Brique 2) — forecasting derrière une frontière de service.

FastAPI léger, **autonome** (aucune dépendance au backend), **keyless** : démarre
sans aucune clé. Expose `/train`, `/predict`, `/model/version`. L'API principale
l'appelle via `ForecastServiceClient` (mode `http`) et **retombe en in-process**
s'il est indisponible — on ne casse jamais la demande.

Le modèle par défaut est une moyenne mobile + saisonnalité hebdomadaire (même
esprit que le modèle `naive` du backend), suffisant pour valider la frontière de
service ; brancher Prophet/LGBM ici ne change pas le contrat.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from fastapi import FastAPI
from pydantic import BaseModel

MODEL_VERSION = os.environ.get("ML_MODEL_VERSION", "v1")
WINDOW = int(os.environ.get("ML_WINDOW", "28"))

app = FastAPI(title="MyHanout ML Service", version="0.1.0")


class HistoryPoint(BaseModel):
    ds: str
    y: float


class PredictRequest(BaseModel):
    product_id: int | None = None
    horizon_days: int = 14
    model: str = "naive"
    history: list[HistoryPoint] = []


class ForecastPoint(BaseModel):
    ds: str
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None


class ForecastResult(BaseModel):
    product_id: int | None = None
    model: str
    horizon_days: int
    points: list[ForecastPoint] = []
    explanation: str | None = None


class TrainRequest(BaseModel):
    product_id: int | None = None
    model: str = "naive"
    history: list[HistoryPoint] = []


# Facteur hebdomadaire simple (week-end plus chargé pour un commerce de proximité).
_WEEKDAY = {0: 0.9, 1: 0.9, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3, 6: 0.7}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.get("/model/version")
def model_version() -> dict:
    return {"model_version": MODEL_VERSION, "window": WINDOW}


@app.post("/train", response_model=dict)
def train(req: TrainRequest) -> dict:
    """Entraînement (stub versionné) : ici la moyenne mobile ne nécessite pas de fit."""
    n = len(req.history)
    return {"model": req.model, "model_version": MODEL_VERSION, "trained_on": n}


@app.post("/predict", response_model=ForecastResult)
def predict(req: PredictRequest) -> ForecastResult:
    if not req.history:
        return ForecastResult(
            product_id=req.product_id,
            model=req.model,
            horizon_days=req.horizon_days,
            points=[],
            explanation="Aucun historique : prévision nulle.",
        )
    hist = sorted(req.history, key=lambda p: p.ds)
    recent = hist[-WINDOW:]
    baseline = sum(p.y for p in recent) / len(recent)
    last = date.fromisoformat(hist[-1].ds)
    points: list[ForecastPoint] = []
    for i in range(1, req.horizon_days + 1):
        day = last + timedelta(days=i)
        yhat = baseline * _WEEKDAY.get(day.weekday(), 1.0)
        points.append(
            ForecastPoint(
                ds=day.isoformat(),
                yhat=round(yhat, 2),
                yhat_lower=round(yhat * 0.8, 2),
                yhat_upper=round(yhat * 1.2, 2),
            )
        )
    return ForecastResult(
        product_id=req.product_id,
        model=req.model,
        horizon_days=req.horizon_days,
        points=points,
        explanation=(
            f"[ml-service {MODEL_VERSION}] moyenne mobile {len(recent)}j "
            f"(base={baseline:.1f}) × saisonnalité hebdo."
        ),
    )
