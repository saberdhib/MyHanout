"""Registre de modèles (MLOps) : versionne les modèles entraînés + réentraînement.

Ferme la boucle MLOps : entraîner → mesurer (MAE/MAPE) → **versionner** → activer, avec
un déclencheur tracé (manuel / planifié / dérive). Un seul artefact actif par
(produit, modèle). Le « modèle naïf » est paramétré par sa baseline (moyenne mobile) ;
Prophet/LGBM sérialiseraient leur artefact dans `artifact_uri` (MinIO) — même contrat.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.model_artifact import ModelArtifact, RetrainTrigger
from app.services.mlops_service import _baseline, aggregate_metrics

log = get_logger(__name__)


async def _metrics_for(session: AsyncSession, product_id: int, model_name: str) -> dict:
    """MAE/MAPE + n depuis les évaluations stockées (0/None si pas d'historique)."""
    for row in await aggregate_metrics(session, product_id):
        if row["model"] == model_name:
            return row
    return {"n": 0, "mae": None, "mape": None}


async def register_model(
    session: AsyncSession,
    *,
    product_id: int | None,
    model_name: str,
    baseline: float,
    mae: float | None,
    mape: float | None,
    n_observations: int,
    trigger: RetrainTrigger,
    artifact_uri: str | None = None,
) -> ModelArtifact:
    """Enregistre une nouvelle version active, désactive la précédente (même produit/modèle).

    La désactivation charge les instances actives (SELECT filtré par le garde-fou) puis
    les mute — pas d'`UPDATE` en masse (que le garde-fou ne couvrirait pas).
    """
    previous = list(
        await session.scalars(
            select(ModelArtifact).where(
                ModelArtifact.product_id == product_id,
                ModelArtifact.model_name == model_name,
                ModelArtifact.active.is_(True),
            )
        )
    )
    for art in previous:
        art.active = False

    count = await session.scalar(
        select(func.count())
        .select_from(ModelArtifact)
        .where(
            ModelArtifact.product_id == product_id,
            ModelArtifact.model_name == model_name,
        )
    )
    version = f"v{(count or 0) + 1}"
    artifact = ModelArtifact(
        product_id=product_id,
        model_name=model_name,
        version=version,
        baseline=round(baseline, 4),
        n_observations=n_observations,
        mae=mae,
        mape=mape,
        trigger=trigger,
        active=True,
        artifact_uri=artifact_uri,
        trained_at=datetime.now(UTC),
    )
    session.add(artifact)
    await session.flush()
    log.info(
        "mlops.model_registered",
        product_id=product_id,
        model=model_name,
        version=version,
        trigger=str(trigger),
    )
    return artifact


async def retrain_product(
    session: AsyncSession,
    product_id: int,
    *,
    model_name: str = "naive",
    trigger: RetrainTrigger = RetrainTrigger.MANUAL,
) -> ModelArtifact:
    """Réentraîne (recalcule la baseline) un produit et enregistre une version."""
    baseline = await _baseline(session, product_id)
    metrics = await _metrics_for(session, product_id, model_name)
    return await register_model(
        session,
        product_id=product_id,
        model_name=model_name,
        baseline=baseline,
        mae=metrics["mae"],
        mape=metrics["mape"],
        n_observations=int(metrics["n"]),
        trigger=trigger,
    )


async def retrain_all(
    session: AsyncSession,
    *,
    model_name: str = "naive",
    trigger: RetrainTrigger = RetrainTrigger.SCHEDULED,
) -> list[ModelArtifact]:
    """Réentraîne tous les produits du commerce courant (cycle planifié)."""
    from app.models.product import Product

    ids = list(await session.scalars(select(Product.id)))
    return [
        await retrain_product(session, pid, model_name=model_name, trigger=trigger) for pid in ids
    ]


async def retrain_on_drift(
    session: AsyncSession,
    *,
    mape_threshold: float,
    model_name: str = "naive",
) -> list[ModelArtifact]:
    """Réentraîne uniquement les produits dont la MAPE dépasse le seuil (dérive)."""
    retrained: list[ModelArtifact] = []
    for row in await aggregate_metrics(session):
        if row["model"] != model_name:
            continue
        mape = row["mape"]
        if mape is not None and mape > mape_threshold:
            retrained.append(
                await retrain_product(
                    session, row["product_id"], model_name=model_name, trigger=RetrainTrigger.DRIFT
                )
            )
    return retrained


async def list_models(
    session: AsyncSession, product_id: int | None = None, *, active_only: bool = False
) -> list[ModelArtifact]:
    stmt = select(ModelArtifact).order_by(ModelArtifact.id.desc())
    if product_id is not None:
        stmt = stmt.where(ModelArtifact.product_id == product_id)
    if active_only:
        stmt = stmt.where(ModelArtifact.active.is_(True))
    return list(await session.scalars(stmt))


async def active_model(
    session: AsyncSession, product_id: int, *, model_name: str = "naive"
) -> ModelArtifact | None:
    return await session.scalar(
        select(ModelArtifact).where(
            ModelArtifact.product_id == product_id,
            ModelArtifact.model_name == model_name,
            ModelArtifact.active.is_(True),
        )
    )
