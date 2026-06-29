"""Service factures : ingestion (OCR→parse→valide) + revue humaine + persistance.

Parcours :
1. `ingest_and_store` : OCR + parsing + validation, crée l'invoice en
   `pending_review`. Les lignes ne sont PAS écrites (attente de validation).
   Idempotent par hash de fichier.
2. `approve_invoice` : un humain valide -> écrit les `invoice_line`, statut
   `approved`, trace d'audit.
3. `reject_invoice` : un humain rejette avec motif -> statut `rejected`, audit.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.ingestion.ocr import extract_with_fallback
from app.ingestion.parsing.invoice_parser import ParsedInvoice, parse_invoice
from app.ingestion.validation.validators import validate_invoice
from app.models.base import InvoiceStatus, OcrStatus
from app.models.invoice import Invoice, InvoiceLine
from app.models.supplier import Supplier

log = get_logger(__name__)

# Seuil sous lequel la confiance OCR est jugée faible (motif de review).
_LOW_CONFIDENCE = 0.6


def _build_reasons(parsed: ParsedInvoice, report, confidence: float) -> list[str]:
    """Explicabilité : pourquoi la facture nécessite une revue humaine."""
    reasons: list[str] = []
    if confidence < _LOW_CONFIDENCE:
        reasons.append(f"Confiance OCR faible ({confidence:.2f}).")
    for issue in report.issues:
        reasons.append(f"[{issue.level}] {issue.field}: {issue.message}")
    if not parsed.supplier_name:
        reasons.append("Fournisseur non identifié.")
    if not reasons:
        reasons.append("Validation humaine requise avant écriture en base.")
    return reasons


async def _match_supplier(session: AsyncSession, name: str | None) -> Supplier | None:
    if not name:
        return None
    return await session.scalar(select(Supplier).where(Supplier.name == name))


async def ingest_and_store(
    session: AsyncSession,
    content: bytes,
    *,
    content_type: str = "application/pdf",
    filename: str | None = None,
    user_id: int | None = None,
) -> tuple[Invoice, list[str]]:
    """Ingestion d'un document → invoice en `pending_review`. Idempotent (hash)."""
    file_hash = hashlib.sha256(content).hexdigest()

    existing = await session.scalar(select(Invoice).where(Invoice.file_hash == file_hash))
    if existing:
        log.info("invoice.ingest.duplicate", invoice_id=existing.id, file_hash=file_hash)
        report = json.loads(existing.validation_report or "{}")
        return existing, report.get("reasons", ["Document déjà importé."])

    # OCR résilient (jamais d'échec dur), puis parsing + validation.
    ocr = await extract_with_fallback(content, content_type=content_type)
    parsed = parse_invoice(ocr)
    report = validate_invoice(parsed)
    reasons = _build_reasons(parsed, report, ocr.confidence)

    supplier = await _match_supplier(session, parsed.supplier_name)
    report_payload = {
        "parsed": parsed.model_dump(mode="json"),
        "validation": report.model_dump(mode="json"),
        "reasons": reasons,
        "ocr_provider": ocr.provider,
    }

    invoice = Invoice(
        number=parsed.number,
        supplier_id=supplier.id if supplier else None,
        issue_date=parsed.issue_date,
        due_date=parsed.due_date,
        total_amount=parsed.total_amount,
        currency=parsed.currency,
        status=InvoiceStatus.PENDING_REVIEW,
        ocr_status=OcrStatus.DONE if ocr.text.strip() else OcrStatus.FAILED,
        ocr_confidence=ocr.confidence,
        source_uri=filename,
        file_hash=file_hash,
        validation_report=json.dumps(report_payload, ensure_ascii=False),
    )
    session.add(invoice)
    await session.flush()
    await record_audit(
        session,
        action="invoice.upload",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=f"provider={ocr.provider}; lines={len(parsed.lines)}",
    )
    log.info(
        "invoice.ingest.done",
        invoice_id=invoice.id,
        provider=ocr.provider,
        lines=len(parsed.lines),
        confidence=ocr.confidence,
    )
    return invoice, reasons


async def approve_invoice(session: AsyncSession, invoice_id: int, *, user_id: int) -> Invoice:
    """Validation humaine : écrit les lignes parsées + audit. Aucun écrit auto."""
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")
    if invoice.status != InvoiceStatus.PENDING_REVIEW:
        raise AppError(
            f"Facture {invoice_id} non en attente de revue (statut={invoice.status}).",
            code="invalid_state",
        )

    payload = json.loads(invoice.validation_report or "{}")
    parsed = ParsedInvoice.model_validate(payload.get("parsed", {}))

    total = 0.0
    for line in parsed.lines:
        total += line.line_total
        session.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
            )
        )
    if total:
        invoice.total_amount = total
    invoice.status = InvoiceStatus.APPROVED
    invoice.reviewed_by_id = user_id
    invoice.reviewed_at = datetime.now(UTC)
    await record_audit(
        session,
        action="invoice.approve",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=f"lines_written={len(parsed.lines)}",
    )
    log.info("invoice.approved", invoice_id=invoice.id, lines=len(parsed.lines))
    return invoice


async def reject_invoice(
    session: AsyncSession, invoice_id: int, *, user_id: int, reason: str
) -> Invoice:
    """Rejet humain avec motif (tracé). Aucune ligne écrite."""
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")
    if invoice.status != InvoiceStatus.PENDING_REVIEW:
        raise AppError(
            f"Facture {invoice_id} non en attente de revue (statut={invoice.status}).",
            code="invalid_state",
        )
    invoice.status = InvoiceStatus.REJECTED
    invoice.review_reason = reason
    invoice.reviewed_by_id = user_id
    invoice.reviewed_at = datetime.now(UTC)
    await record_audit(
        session,
        action="invoice.reject",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=reason,
    )
    log.info("invoice.rejected", invoice_id=invoice.id, reason=reason)
    return invoice


async def update_invoice(
    session: AsyncSession, invoice_id: int, *, user_id: int, fields: dict
) -> Invoice:
    """Édition manuelle (champs pré-remplis) + bascule payé/non payé, auditée."""
    invoice = await session.get(Invoice, invoice_id)  # filtré par tenant
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")
    for key in ("number", "supplier_id", "issue_date", "due_date", "total_amount"):
        if fields.get(key) is not None:
            setattr(invoice, key, fields[key])
    if fields.get("paid") is not None:
        invoice.paid = bool(fields["paid"])
        invoice.paid_at = datetime.now(UTC) if invoice.paid else None
        if invoice.paid:
            invoice.status = InvoiceStatus.PAID
    await record_audit(
        session,
        action="invoice.update",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=f"fields={sorted(k for k, v in fields.items() if v is not None)}",
    )
    log.info("invoice.updated", invoice_id=invoice.id)
    return invoice
