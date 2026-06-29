"""Tracing léger : corrélation des logs par requête + OpenTelemetry optionnel.

Chaque requête reçoit un `request_id` (et reprend le `trace_id` W3C `traceparent`
s'il est fourni). Ces identifiants sont liés au contexte structlog → tous les logs
de la requête sont corrélés, et renvoyés dans l'en-tête `X-Request-ID`.

Si `OTEL_ENABLED=true` et qu'OpenTelemetry est installé, on initialise un tracer
(exporter console par défaut). Sinon, no-op : aucune dépendance requise.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.logging import get_logger

log = get_logger("tracing")


def setup_tracing() -> None:
    """Initialise OpenTelemetry si activé et disponible (sinon no-op)."""
    if not settings.otel_enabled:
        return
    try:  # pragma: no cover - dépend d'une lib optionnelle
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        log.info("tracing.otel.enabled", service=settings.service_name)
    except ImportError:
        log.warning("tracing.otel.unavailable", hint="pip install opentelemetry-sdk")


def _trace_id_from_header(traceparent: str | None) -> str | None:
    # W3C traceparent: version-traceid-spanid-flags
    if traceparent and traceparent.count("-") >= 2:
        parts = traceparent.split("-")
        if len(parts) >= 2 and len(parts[1]) == 32:
            return parts[1]
    return None


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex
        trace_id = _trace_id_from_header(request.headers.get("traceparent")) or request_id
        structlog.contextvars.bind_contextvars(request_id=request_id, trace_id=trace_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id", "trace_id")
        response.headers["X-Request-ID"] = request_id
        return response
