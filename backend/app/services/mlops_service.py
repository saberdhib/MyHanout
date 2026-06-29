"""Boucle MLOps : mesure l'écart prévu/réel, agrège MAE/MAPE, réentraîne.

Sobre et explicite (pas d'infra lourde) : la valeur démontrée est la *boucle
fermée* réel → mesure d'erreur → amélioration.

Définition de la demande RÉELLE (variante A, par défaut) :
    réel = stock_veille + quantité_commandée − stock_soir
Si pas de saisie la veille, on retombe (variante B) sur réel = quantité_commandée
(proxy), signalé dans les logs.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.intelligence.forecasting.features import (
    festival_factor,
    is_holiday,
    weekday_factor,
)
from app.models.daily_entry import DailyEntry
from app.models.forecast_evaluation import ForecastEvaluation
from app.repositories.sale import SaleRepository

log = get_logger(__name__)

# Version du modèle utilisée pour les prévisions (traçabilité MLOps).
MODEL_VERSION = "naive-v1"
_BASELINE_WINDOW = 28


async def _baseline(session: AsyncSession, product_id: int) -> float:
    """Moyenne mobile récente des ventes journalières (base du modèle naïf)."""
    history = await SaleRepository(session).daily_history(product_id)
    if not history:
        return 0.0
    recent = history[-_BASELINE_WINDOW:]
    return sum(y for _, y in recent) / len(recent)


def predicted_demand(baseline: float, day: date) -> float:
    """Prévision (même formule que NaiveForecastModel) pour un jour donné."""
    if is_holiday(day):
        return 0.0
    return round(baseline * weekday_factor(day) * festival_factor(day), 2)


async def _actual_demand(session: AsyncSession, entry: DailyEntry) -> float:
    """Demande réelle déduite de la commande + variation de stock."""
    prev = await session.scalar(
        select(DailyEntry).where(
            DailyEntry.product_id == entry.product_id,
            DailyEntry.entry_date == entry.entry_date - timedelta(days=1),
        )
    )
    if prev is not None:
        return max(
            0.0,
            float(prev.stock_remaining)
            + float(entry.quantity_ordered)
            - float(entry.stock_remaining),
        )
    # Variante B (proxy) : pas de stock la veille.
    log.info("mlops.actual.proxy", product_id=entry.product_id, date=str(entry.entry_date))
    return float(entry.quantity_ordered)


async def evaluate_entry(session: AsyncSession, entry: DailyEntry) -> ForecastEvaluation:
    """Calcule et persiste l'écart prévu/réel pour une saisie (idempotent)."""
    baseline = await _baseline(session, entry.product_id)
    predicted = predicted_demand(baseline, entry.entry_date)
    actual = await _actual_demand(session, entry)
    error_abs = round(abs(predicted - actual), 4)
    error_pct = round(error_abs / actual, 4) if actual > 0 else None

    existing = await session.scalar(
        select(ForecastEvaluation).where(
            ForecastEvaluation.product_id == entry.product_id,
            ForecastEvaluation.eval_date == entry.entry_date,
            ForecastEvaluation.model == "naive",
        )
    )
    if existing:
        existing.predicted = predicted
        existing.actual = actual
        existing.error_abs = error_abs
        existing.error_pct = error_pct
        existing.model_version = MODEL_VERSION
        evaluation = existing
    else:
        evaluation = ForecastEvaluation(
            product_id=entry.product_id,
            eval_date=entry.entry_date,
            predicted=predicted,
            actual=actual,
            error_abs=error_abs,
            error_pct=error_pct,
            model="naive",
            model_version=MODEL_VERSION,
        )
        session.add(evaluation)
    await session.flush()
    log.info(
        "mlops.evaluated",
        product_id=entry.product_id,
        predicted=predicted,
        actual=actual,
        error_abs=error_abs,
    )
    return evaluation


async def aggregate_metrics(session: AsyncSession, product_id: int | None = None) -> list[dict]:
    """Agrège MAE/MAPE par produit (et modèle) sur les évaluations stockées."""
    query = select(
        ForecastEvaluation.product_id,
        ForecastEvaluation.model,
        func.count().label("n"),
        func.avg(ForecastEvaluation.error_abs).label("mae"),
        func.avg(ForecastEvaluation.error_pct).label("mape"),
    ).group_by(ForecastEvaluation.product_id, ForecastEvaluation.model)
    if product_id:
        query = query.where(ForecastEvaluation.product_id == product_id)

    rows = await session.execute(query)
    return [
        {
            "product_id": r.product_id,
            "model": r.model,
            "n": int(r.n),
            "mae": round(float(r.mae), 4) if r.mae is not None else None,
            "mape": round(float(r.mape), 4) if r.mape is not None else None,
        }
        for r in rows.all()
    ]


async def retrain(session: AsyncSession, product_id: int | None = None) -> dict:
    """Réentraîne le modèle naïf (recalcule la baseline) à partir de l'historique
    enrichi par les saisies réelles, et renvoie la nouvelle version.

    Le modèle naïf est paramétré par sa baseline (moyenne mobile) ; le
    « réentraînement » consiste à la recalculer. Prophet/LGBM (si dispo)
    seraient ré-ajustés ici de la même façon.
    """
    from app.models.product import Product

    query = select(Product.id)
    if product_id:
        query = query.where(Product.id == product_id)
    ids = list((await session.scalars(query)).all())

    updated = {pid: await _baseline(session, pid) for pid in ids}
    log.info("mlops.retrain", products=len(updated), version=MODEL_VERSION)
    return {
        "model": "naive",
        "model_version": MODEL_VERSION,
        "products_retrained": len(updated),
        "baselines": {str(k): round(v, 2) for k, v in updated.items()},
    }
