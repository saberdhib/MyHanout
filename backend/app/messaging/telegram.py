"""Client Telegram (Bot API) derrière la même forme que le client WhatsApp.

`bot` = implémentation réelle (sendMessage / getFile + download) ; `mock` =
journalisation locale (défaut keyless). Sélection via TELEGRAM_PROVIDER.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.messaging.whatsapp.base import SendResult

log = get_logger(__name__)


class TelegramClient(ABC):
    name: str = "abstract"

    @abstractmethod
    async def send_text(self, chat_id: str, text: str) -> SendResult: ...

    @abstractmethod
    async def download_media(self, file_id: str) -> bytes: ...


class MockTelegramClient(TelegramClient):
    name = "mock"

    def __init__(self) -> None:
        self.outbox: list[tuple[str, str]] = []

    async def send_text(self, chat_id: str, text: str) -> SendResult:
        self.outbox.append((chat_id, text))
        log.info("telegram.mock.send", chat_id=chat_id, text=text)
        return SendResult(
            success=True, message_id=f"tg-mock-{len(self.outbox)}", provider=self.name
        )

    async def download_media(self, file_id: str) -> bytes:
        log.info("telegram.mock.download", file_id=file_id)
        return b"%PDF-1.4 telegram-mock-invoice"


class BotTelegramClient(TelegramClient):
    """Implémentation réelle Telegram Bot API."""

    name = "bot"

    def __init__(
        self, token: str | None = None, http_client: httpx.AsyncClient | None = None
    ) -> None:
        self.token = token or settings.telegram_bot_token
        self.api = f"https://api.telegram.org/bot{self.token}"
        self.file_api = f"https://api.telegram.org/file/bot{self.token}"
        self._http = http_client

    def _require(self) -> None:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN manquant. Utilisez TELEGRAM_PROVIDER=mock.")

    async def send_text(self, chat_id: str, text: str) -> SendResult:
        self._require()
        client = self._http or httpx.AsyncClient(timeout=30)
        owns = self._http is None
        try:
            resp = await client.post(
                f"{self.api}/sendMessage", json={"chat_id": chat_id, "text": text}
            )
            resp.raise_for_status()
            msg_id = str(resp.json().get("result", {}).get("message_id", ""))
            log.info("telegram.bot.sent", chat_id=chat_id, message_id=msg_id)
            return SendResult(success=True, message_id=msg_id, provider=self.name)
        finally:
            if owns:
                await client.aclose()

    async def download_media(self, file_id: str) -> bytes:
        self._require()
        client = self._http or httpx.AsyncClient(timeout=30)
        owns = self._http is None
        try:
            meta = await client.get(f"{self.api}/getFile", params={"file_id": file_id})
            meta.raise_for_status()
            file_path = meta.json()["result"]["file_path"]
            binary = await client.get(f"{self.file_api}/{file_path}")
            binary.raise_for_status()
            return binary.content
        finally:
            if owns:
                await client.aclose()


def get_telegram_client() -> TelegramClient:
    """Retourne le client Telegram configuré ; mock si pas de token (keyless)."""
    if settings.telegram_provider.lower() == "bot" and settings.telegram_bot_token:
        return BotTelegramClient()
    if settings.telegram_provider.lower() == "bot":
        log.warning("telegram.provider.fallback", reason="no token", to="mock")
    return MockTelegramClient()
