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
from app.schemas.common import HealthResponse

configure_logging()
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

    register_exception_handlers(app)
    setup_metrics(app)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    log.info("app.started", env=settings.env, version=__version__)
    return app


app = create_app()
