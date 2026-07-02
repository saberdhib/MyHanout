"""Backtest de prévision : mesure honnête de chaque modèle sur un holdout.

Répond à « le modèle avancé bat-il vraiment le naïf ? » de façon vérifiable :
validation glissante (walk-forward) sur l'historique réel, MAE/MAPE par modèle.
Inclut une baseline « moyenne plate » (sans saisonnalité) pour prouver que le harnais
discrimine réellement. Prophet/LGBM sont testés s'ils sont installés, sinon signalés
« indisponible » (aucune dépendance dure).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.intelligence.forecasting import get_forecast_model
from app.intelligence.forecasting.base import ForecastModel, HistoryPoint

_CANDIDATES = ["mean", "naive", "prophet", "lgbm"]


@dataclass
class ModelScore:
    model: str
    available: bool
    mae: float | None = None
    mape: float | None = None  # 0..1
    n_points: int = 0
    note: str | None = None


@dataclass
class BacktestReport:
    product_id: int | None
    horizon_days: int
    folds: int
    history_points: int
    results: list[ModelScore] = field(default_factory=list)
    best_model: str | None = None
    verdict: str = ""


def _metrics(pairs: list[tuple[float, float]]) -> tuple[float | None, float | None, int]:
    """(MAE, MAPE, n) sur des couples (réel, prévu). MAPE ignore les réels nuls."""
    if not pairs:
        return None, None, 0
    mae = sum(abs(y - yhat) for y, yhat in pairs) / len(pairs)
    pct = [abs(y - yhat) / y for y, yhat in pairs if y > 0]
    mape = sum(pct) / len(pct) if pct else None
    return round(mae, 3), (round(mape, 4) if mape is not None else None), len(pairs)


def _predict_mean(train: list[HistoryPoint], horizon: int) -> dict:
    """Baseline plate : moyenne récente, sans saisonnalité (référence basse)."""
    from datetime import timedelta

    if not train:
        return {}
    window = train[-28:]
    base = sum(p.y for p in window) / len(window)
    last = train[-1].ds
    return {last + timedelta(days=i): base for i in range(1, horizon + 1)}


def _predict_model(model: ForecastModel, train: list[HistoryPoint], horizon: int) -> dict:
    res = model.predict(train, horizon_days=horizon)
    return {p.ds: p.yhat for p in res.points}


def backtest_history(
    history: list[HistoryPoint], *, horizon_days: int = 7, folds: int = 3
) -> BacktestReport:
    """Walk-forward : pour chaque pli, on entraîne sur le passé et on teste l'horizon suivant."""
    history = sorted(history, key=lambda p: p.ds)
    n = len(history)
    report = BacktestReport(
        product_id=None, horizon_days=horizon_days, folds=folds, history_points=n
    )

    # Il faut assez d'historique : au moins une fenêtre + les plis d'horizon.
    min_needed = 28 + horizon_days * folds
    if n < min_needed:
        report.verdict = (
            f"Historique insuffisant ({n} jours) pour un backtest fiable "
            f"(≥ {min_needed} recommandés)."
        )
        return report

    actual_by_ds = {p.ds: p.y for p in history}

    for name in _CANDIDATES:
        # Construction + prédiction dans un même garde : prophet/lgbm lèvent (à
        # l'instanciation OU à predict) si la lib n'est pas installée → « indisponible ».
        try:
            model: ForecastModel | None = None if name == "mean" else get_forecast_model(name)
            pairs: list[tuple[float, float]] = []
            for fold in range(folds):
                cutoff = n - horizon_days * (fold + 1)
                if cutoff < 28:
                    break
                train = history[:cutoff]
                preds = (
                    _predict_mean(train, horizon_days)
                    if model is None
                    else _predict_model(model, train, horizon_days)
                )
                for ds, yhat in preds.items():
                    if ds in actual_by_ds:
                        pairs.append((actual_by_ds[ds], yhat))
            mae, mape, npts = _metrics(pairs)
            report.results.append(
                ModelScore(model=name, available=True, mae=mae, mape=mape, n_points=npts)
            )
        except Exception as exc:  # lib non installée / modèle indisponible
            report.results.append(ModelScore(model=name, available=False, note=str(exc)))

    _verdict(report)
    return report


def _verdict(report: BacktestReport) -> None:
    scored = [r for r in report.results if r.available and r.mape is not None]
    if not scored:
        report.verdict = "Aucun modèle évaluable sur cet historique."
        return
    best = min(scored, key=lambda r: r.mape)  # type: ignore[arg-type,return-value]
    report.best_model = best.model
    naive = next((r for r in scored if r.model == "naive"), None)
    mean = next((r for r in scored if r.model == "mean"), None)

    parts = [f"Meilleur modèle : **{best.model}** (MAPE {best.mape:.0%})."]
    if naive and mean and naive.mape is not None and mean.mape is not None and mean.mape > 0:
        gain = (mean.mape - naive.mape) / mean.mape
        if gain > 0.02:
            parts.append(
                f"La saisonnalité (naïf) réduit l'erreur de {gain:.0%} vs moyenne plate "
                "→ le harnais discrimine bien."
            )
    advanced = [r for r in scored if r.model in ("prophet", "lgbm")]
    if not advanced:
        parts.append(
            "Prophet/LGBM non installés : le naïf saisonnier reste la référence "
            "(installer les libs pour tenter de le battre)."
        )
    report.verdict = " ".join(parts)
