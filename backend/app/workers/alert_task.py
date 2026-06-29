"""Tâche Celery : génération d'alertes stock (rupture/péremption) (stub)."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.repositories.stock import StockRepository
from app.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="alert.scan_stock")
def scan_stock_alerts(expiring_within_days: int = 7) -> dict:
    """Détecte les stocks en rupture et proches de la péremption."""

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            repo = StockRepository(session)
            low = await repo.list_low_stock()
            expiring = await repo.list_expiring(within_days=expiring_within_days)
            return {"low_stock": len(low), "expiring": len(expiring)}

    out = asyncio.run(_run())
    log.info("alert_task.done", **out)
    return out
