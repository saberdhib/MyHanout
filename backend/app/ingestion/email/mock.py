"""Boîte mail mock (keyless) : renvoie des messages factices avec pièce jointe.

Permet de démontrer l'import « depuis la boîte mail » sans aucune connexion IMAP.
Le contenu est un PDF minimal valide pour traverser le pipeline OCR mock.
"""

from __future__ import annotations

from app.ingestion.email.base import MailAttachment, MailboxProvider, MailMessage

# PDF minimal (suffisant pour l'OCR mock/fallback).
_FAKE_PDF = b"%PDF-1.4 mock-invoice-from-email"


class MockMailboxProvider(MailboxProvider):
    name = "mock"

    async def fetch_unread(self, *, limit: int = 10) -> list[MailMessage]:
        messages = [
            MailMessage(
                message_id="mock-001",
                sender="fournisseur.viande@example.com",
                subject="Facture FAC-2026-0420",
                attachments=[
                    MailAttachment(
                        filename="FAC-2026-0420.pdf",
                        content_type="application/pdf",
                        content=_FAKE_PDF + b" 0420",
                    )
                ],
            ),
            MailMessage(
                message_id="mock-002",
                sender="primeur.local@example.com",
                subject="Bon de commande BC-77",
                attachments=[
                    MailAttachment(
                        filename="BC-77.pdf",
                        content_type="application/pdf",
                        content=_FAKE_PDF + b" BC77",
                    )
                ],
            ),
        ]
        return messages[:limit]
