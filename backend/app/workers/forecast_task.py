"""Tâche Celery : recalcul périodique des prévisions (stub)."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.forecast_service import forecast_product
from app.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="forecast.run_product")
def run_product_forecast(product_id: int, horizon_days: int = 14) -> dict:
    """Calcule et renvoie la prévision d'un produit."""

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await forecast_product(session, product_id, horizon_days=horizon_days)
            return result.model_dump(mode="json")

    out = asyncio.run(_run())
    log.info("forecast_task.done", product_id=product_id)
    return out
