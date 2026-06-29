"""Boîte mail réelle via IMAP (imaplib, stdlib). Activée par env si configurée.

Récupère les messages non lus du dossier configuré, extrait les pièces jointes
(PDF/images), puis laisse l'ingestion facture faire le reste. Sans hôte/identifiants
→ erreur explicite (la fabrique retombe alors sur le mock).
"""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.email.base import MailAttachment, MailboxProvider, MailMessage

log = get_logger(__name__)

_ATTACH_TYPES = ("application/pdf", "image/")


class ImapMailboxProvider(MailboxProvider):
    name = "imap"

    def __init__(self) -> None:
        self.host = settings.email_imap_host
        self.port = settings.email_imap_port
        self.user = settings.email_imap_user
        self.password = settings.email_imap_password
        self.folder = settings.email_imap_folder

    def _require(self) -> None:
        if not (self.host and self.user and self.password):
            raise RuntimeError("Config IMAP incomplète. Utilisez EMAIL_PROVIDER=mock.")

    async def fetch_unread(self, *, limit: int = 10) -> list[MailMessage]:  # pragma: no cover
        import contextlib
        import email
        import imaplib

        self._require()
        out: list[MailMessage] = []
        client = imaplib.IMAP4_SSL(self.host, self.port)
        try:
            client.login(self.user, self.password)
            client.select(self.folder)
            _, data = client.search(None, "UNSEEN")
            ids = data[0].split()[:limit]
            for num in ids:
                _, msg_data = client.fetch(num, "(RFC822)")
                first = msg_data[0]
                if not isinstance(first, tuple):
                    continue
                parsed = email.message_from_bytes(first[1])
                attachments: list[MailAttachment] = []
                for part in parsed.walk():
                    ctype = part.get_content_type()
                    if not ctype.startswith(_ATTACH_TYPES) and ctype != "application/pdf":
                        continue
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    attachments.append(
                        MailAttachment(
                            filename=part.get_filename() or f"{num.decode()}.bin",
                            content_type=ctype,
                            content=payload,
                        )
                    )
                if attachments:
                    out.append(
                        MailMessage(
                            message_id=parsed.get("Message-ID", num.decode()),
                            sender=parsed.get("From", ""),
                            subject=parsed.get("Subject", ""),
                            attachments=attachments,
                        )
                    )
            log.info("email.imap.fetched", messages=len(out))
            return out
        finally:
            with contextlib.suppress(Exception):  # best effort cleanup
                client.logout()
