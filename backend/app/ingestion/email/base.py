"""Contrat des providers de boîte mail (récupération de factures/bons de commande).

Abstraction commune : on récupère des messages non lus contenant des pièces
jointes (PDF/images), qui partent ensuite dans le pipeline d'ingestion facture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class MailAttachment(BaseModel):
    filename: str
    content_type: str
    content: bytes


class MailMessage(BaseModel):
    message_id: str
    sender: str
    subject: str
    attachments: list[MailAttachment] = []


class MailboxProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def fetch_unread(self, *, limit: int = 10) -> list[MailMessage]:
        """Récupère les messages non lus avec pièces jointes (idempotent côté ingestion)."""
        raise NotImplementedError
