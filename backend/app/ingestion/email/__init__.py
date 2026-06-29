"""Récupération de factures depuis une boîte mail (abstraction + mock keyless)."""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.email.base import MailAttachment, MailboxProvider, MailMessage
from app.ingestion.email.mock import MockMailboxProvider

log = get_logger(__name__)


def get_mailbox_provider() -> MailboxProvider:
    """Retourne le provider de boîte mail configuré. Sans config → mock (keyless)."""
    provider = settings.email_provider.lower()
    if provider == "imap" and settings.email_imap_host:
        from app.ingestion.email.imap import ImapMailboxProvider

        return ImapMailboxProvider()
    if provider == "imap":
        log.warning("email.provider.fallback", reason="no host", to="mock")
    return MockMailboxProvider()


__all__ = [
    "MailAttachment",
    "MailMessage",
    "MailboxProvider",
    "get_mailbox_provider",
]
