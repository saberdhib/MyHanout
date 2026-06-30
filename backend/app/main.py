"""Point d'entrée FastAPI : app, middlewares, routers, healthcheck."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.config import settings
from app.core.audit import AuditMiddleware
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.metrics import setup_metrics
from app.core.rate_limit import RateLimitMiddleware
from app.core.tracing import TracingMiddleware, setup_tracing
from app.schemas.common import HealthResponse

configure_logging()
setup_tracing()
log = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MyHanout AI API",
        version=__version__,
        description="Copilot IA pour commerces de proximité.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    # Ajouté en dernier => middleware le plus externe : corrèle tous les logs.
    app.add_middleware(TracingMiddleware)

    register_exception_handlers(app)
    setup_metrics(app)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        from app.core.health import check_components

        components = await check_components()
        # Liveness reste "ok" tant que la DB répond ; les dépendances sont indicatives.
        status = "ok" if components.get("database") == "ok" else "degraded"
        return HealthResponse(version=__version__, status=status, components=components)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    log.info("app.started", env=settings.env, version=__version__)
    return app


app = create_app()
