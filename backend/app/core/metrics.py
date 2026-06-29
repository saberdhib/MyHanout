"""Métriques Prometheus + endpoint d'exposition."""

from __future__ import annotations

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

REQUEST_COUNT = Counter(
    "myhanout_requests_total",
    "Nombre total de requêtes HTTP",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "myhanout_request_latency_seconds",
    "Latence des requêtes HTTP",
    ["method", "path"],
)


def setup_metrics(app: FastAPI) -> None:
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
