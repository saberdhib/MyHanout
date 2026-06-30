"""Health checks étendus (Brique 7) : DB, Redis, ml-service.

Best-effort : chaque sonde est isolée (jamais d'exception propagée) pour que
`/health` reste un liveness fiable. Les composants non configurés sont `skipped`.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.config import settings
from app.db.session import engine


async def _check_db() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "down"


async def _check_redis() -> str:
    # Sqlite/local de test : pas de redis requis → on ne fait pas échouer le health.
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            await asyncio.wait_for(client.ping(), timeout=1.5)
            return "ok"
        finally:
            await client.aclose()
    except Exception:
        return "down"


async def _check_ml_service() -> str:
    if settings.forecast_service_client.lower() != "http":
        return "skipped"  # mode in-process : service non requis
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2) as http:
            resp = await http.get(f"{settings.ml_service_url}/health")
            return "ok" if resp.status_code == 200 else "down"
    except Exception:
        return "down"


async def check_components() -> dict[str, str]:
    """Sonde les dépendances en parallèle ; renvoie un dict composant→état."""
    db, redis_state, ml = await asyncio.gather(_check_db(), _check_redis(), _check_ml_service())
    return {"database": db, "redis": redis_state, "ml_service": ml}
