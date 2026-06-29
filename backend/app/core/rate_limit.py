"""Rate limiting applicatif (fenêtre glissante en mémoire).

Défaut : limite par client (utilisateur authentifié si possible, sinon IP).
Implémentation in-memory (suffisante mono-instance / tests) ; en production
multi-instances, brancher un backend Redis derrière la même interface.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.logging import get_logger

log = get_logger("rate_limit")

# Chemins exemptés (probes & métriques).
_EXEMPT = {"/health", "/metrics"}


class _SlidingWindow:
    """Fenêtre glissante de 60 s par clé (timestamps monotones)."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float) -> bool:
        window = self._hits[key]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int | None = None) -> None:
        super().__init__(app)
        self._limiter = _SlidingWindow(limit or settings.rate_limit_per_minute)

    def _client_key(self, request: Request) -> str:
        # Préfère l'utilisateur (Authorization) pour ne pas pénaliser un NAT partagé.
        auth = request.headers.get("authorization")
        if auth:
            return f"tok:{hash(auth)}"
        client = request.client
        return f"ip:{client.host if client else 'unknown'}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path in _EXEMPT:
            return await call_next(request)
        key = self._client_key(request)
        if not self._limiter.allow(key, time.monotonic()):
            log.warning("rate_limit.exceeded", path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Trop de requêtes"}},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
