"""Application Celery (broker/result backend Redis)."""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "myhanout",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.ocr_task",
        "app.workers.forecast_task",
        "app.workers.alert_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
