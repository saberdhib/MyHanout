"""Tâche Celery : agrégation périodique des métriques de qualité (MLOps)."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.mlops_service import aggregate_metrics
from app.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="mlops.aggregate_metrics")
def aggregate_quality_metrics() -> list[dict]:
    """Recalcule les agrégats MAE/MAPE (exposables au dashboard / Prometheus)."""

    async def _run() -> list[dict]:
        async with AsyncSessionLocal() as session:
            return await aggregate_metrics(session)

    out = asyncio.run(_run())
    log.info("mlops_task.done", groups=len(out))
    return out
