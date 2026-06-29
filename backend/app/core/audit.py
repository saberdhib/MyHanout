"""Middleware d'audit + métriques (gouvernance / RGPD).

Trace les requêtes mutantes (POST/PUT/PATCH/DELETE) dans le journal structuré
et incrémente les métriques Prometheus. La persistance en base (AuditLog) est
fournie via `record_audit()` pour les actions sensibles explicites.
"""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.models.audit_log import AuditLog

log = get_logger("audit")

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)

        if request.method in _MUTATING:
            log.info(
                "audit.request",
                method=request.method,
                path=path,
                status=response.status_code,
                duration_ms=round(elapsed * 1000, 1),
            )
        return response


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    resource: str | None = None,
    resource_id: int | None = None,
    detail: str | None = None,
) -> None:
    """Persiste une entrée d'audit pour une action sensible explicite."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
        )
    )
    await session.flush()
