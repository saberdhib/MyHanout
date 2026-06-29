"""Pipeline d'ingestion : OCR -> parsing -> validation -> (persistance).

Orchestration de bout en bout d'un document de facture. La persistance est
laissée en stub (à brancher sur le repository Invoice).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.logging import get_logger
from app.ingestion.ocr import get_ocr_provider
from app.ingestion.parsing.invoice_parser import ParsedInvoice, parse_invoice
from app.ingestion.validation.validators import ValidationReport, validate_invoice

log = get_logger(__name__)


class IngestionResult(BaseModel):
    parsed: ParsedInvoice
    validation: ValidationReport
    persisted_invoice_id: int | None = None


async def ingest_invoice_document(
    content: bytes, *, content_type: str = "application/pdf"
) -> IngestionResult:
    """Exécute le pipeline complet sur un document fourni en octets."""
    provider = get_ocr_provider()
    log.info("ingestion.start", provider=provider.name, bytes=len(content))

    ocr = await provider.extract(content, content_type=content_type)
    parsed = parse_invoice(ocr)
    report = validate_invoice(parsed)

    # TODO: si report.ok, normaliser puis persister via InvoiceRepository.
    log.info(
        "ingestion.done",
        supplier=parsed.supplier_name,
        lines=len(parsed.lines),
        valid=report.ok,
    )
    return IngestionResult(parsed=parsed, validation=report)
