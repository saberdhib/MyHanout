"""Endpoints factures : lecture + upload/approve/reject (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.repositories.invoice import InvoiceRepository
from app.schemas.common import ListResponse
from app.schemas.invoice import (
    InvoiceOut,
    InvoiceRejectRequest,
    InvoiceReviewOut,
    InvoiceUpdate,
)
from app.services.email_import_service import (
    EmailImportResult,
    import_invoices_from_mailbox,
)
from app.services.invoice_service import (
    approve_invoice,
    ingest_and_store,
    reject_invoice,
    update_invoice,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=ListResponse[InvoiceOut])
async def list_invoices(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("invoices")),
) -> ListResponse[InvoiceOut]:
    repo = InvoiceRepository(session)
    invoices = await repo.list_with_lines()
    items = [InvoiceOut.model_validate(inv) for inv in invoices]
    return ListResponse(items=items, total=len(items))


@router.post("/upload", response_model=InvoiceReviewOut)
async def upload_invoice(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> InvoiceReviewOut:
    """Importe un document (PDF/photo) → facture en `pending_review`.

    Lance OCR → parsing → validation. N'écrit AUCUNE ligne : un humain doit
    valider via /approve. Idempotent (même fichier → même facture).
    """
    content = await file.read()
    invoice, reasons = await ingest_and_store(
        session,
        content,
        content_type=file.content_type or "application/pdf",
        filename=file.filename,
        user_id=user.id,
    )
    # Charge la collection (vide à ce stade) pour éviter un lazy-load async.
    await session.refresh(invoice, attribute_names=["lines"])
    out = InvoiceReviewOut.model_validate(invoice)
    out.reasons = reasons
    return out


@router.post("/import/email", response_model=EmailImportResult)
async def import_email(
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> EmailImportResult:
    """Récupère les factures reçues par email (mock keyless ou IMAP réel).

    Chaque pièce jointe est ingérée en `pending_review` (idempotent). Aucune
    ligne n'est écrite sans validation humaine via /approve.
    """
    return await import_invoices_from_mailbox(session, user_id=user.id, limit=limit)


@router.post("/{invoice_id}/approve", response_model=InvoiceOut)
async def approve(
    invoice_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> InvoiceOut:
    """Validation humaine : écrit les lignes parsées + audit."""
    invoice = await approve_invoice(session, invoice_id, user_id=user.id)
    await session.refresh(invoice, attribute_names=["lines"])
    return InvoiceOut.model_validate(invoice)


@router.post("/{invoice_id}/reject", response_model=InvoiceOut)
async def reject(
    invoice_id: int,
    body: InvoiceRejectRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> InvoiceOut:
    """Rejet humain avec motif (tracé)."""
    invoice = await reject_invoice(session, invoice_id, user_id=user.id, reason=body.reason)
    await session.refresh(invoice, attribute_names=["lines"])
    return InvoiceOut.model_validate(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
async def patch_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> InvoiceOut:
    """Édite une facture (n°, date, fournisseur, montant) + bascule payé/non payé."""
    invoice = await update_invoice(session, invoice_id, user_id=user.id, fields=body.model_dump())
    await session.refresh(invoice, attribute_names=["lines"])
    return InvoiceOut.model_validate(invoice)
