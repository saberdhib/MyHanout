"""Tâche Celery : ingestion OCR asynchrone d'un document de facture (stub)."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.ingestion.etl.pipeline import ingest_invoice_document
from app.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="ocr.process_document")
def process_document(content: bytes, content_type: str = "application/pdf") -> dict:
    """Exécute le pipeline d'ingestion sur un document fourni en octets."""
    result = asyncio.run(ingest_invoice_document(content, content_type=content_type))
    log.info("ocr_task.done", valid=result.validation.ok)
    return result.model_dump(mode="json")
