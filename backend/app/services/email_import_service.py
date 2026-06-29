"""Import de factures depuis la boîte mail (human-in-the-loop).

Chaque pièce jointe (PDF/image) part dans le pipeline d'ingestion existant :
OCR → parsing → validation → facture en `pending_review`. Idempotent (hash de
fichier) : ré-importer la même pièce ne crée pas de doublon. Aucune écriture de
ligne sans validation humaine.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.ingestion.email import get_mailbox_provider
from app.services.invoice_service import ingest_and_store

log = get_logger(__name__)


class ImportedInvoice(BaseModel):
    invoice_id: int
    filename: str
    sender: str
    reasons: list[str] = []


class EmailImportResult(BaseModel):
    provider: str
    imported: int
    items: list[ImportedInvoice] = []


async def import_invoices_from_mailbox(
    session: AsyncSession, *, user_id: int | None, limit: int = 10
) -> EmailImportResult:
    """Récupère les mails non lus et ingère leurs pièces jointes en factures."""
    provider = get_mailbox_provider()
    messages = await provider.fetch_unread(limit=limit)
    items: list[ImportedInvoice] = []

    for message in messages:
        for attachment in message.attachments:
            invoice, reasons = await ingest_and_store(
                session,
                attachment.content,
                content_type=attachment.content_type,
                filename=attachment.filename,
                user_id=user_id,
            )
            items.append(
                ImportedInvoice(
                    invoice_id=invoice.id,
                    filename=attachment.filename,
                    sender=message.sender,
                    reasons=reasons,
                )
            )

    await record_audit(
        session,
        action="invoice.import_email",
        user_id=user_id,
        resource="invoice",
        detail=f"provider={provider.name} imported={len(items)}",
    )
    log.info("invoice.import_email", provider=provider.name, imported=len(items))
    return EmailImportResult(provider=provider.name, imported=len(items), items=items)
