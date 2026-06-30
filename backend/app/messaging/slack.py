"""Client Slack (Web API) — même forme que les clients WhatsApp/Telegram.

`bot` = implémentation réelle (chat.postMessage via Bearer token) ; `mock` =
journalisation locale (défaut keyless). Sélection via SLACK_PROVIDER. Permet de
piloter MyHanout depuis Slack, comme depuis WhatsApp/Telegram.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.messaging.whatsapp.base import SendResult

log = get_logger(__name__)


class SlackClient(ABC):
    name: str = "abstract"

    @abstractmethod
    async def send_text(self, channel: str, text: str) -> SendResult: ...


class MockSlackClient(SlackClient):
    name = "mock"

    def __init__(self) -> None:
        self.outbox: list[tuple[str, str]] = []

    async def send_text(self, channel: str, text: str) -> SendResult:
        self.outbox.append((channel, text))
        log.info("slack.mock.send", channel=channel, text=text)
        return SendResult(
            success=True, message_id=f"slack-mock-{len(self.outbox)}", provider=self.name
        )


class BotSlackClient(SlackClient):
    """Implémentation réelle Slack Web API (chat.postMessage)."""

    name = "bot"

    def __init__(
        self, token: str | None = None, http_client: httpx.AsyncClient | None = None
    ) -> None:
        self.token = token or settings.slack_bot_token
        self.api = "https://slack.com/api"
        self._http = http_client

    def _require(self) -> None:
        if not self.token:
            raise RuntimeError("SLACK_BOT_TOKEN manquant. Utilisez SLACK_PROVIDER=mock.")

    async def send_text(self, channel: str, text: str) -> SendResult:  # pragma: no cover - réseau
        self._require()
        client = self._http or httpx.AsyncClient(timeout=30)
        owns = self._http is None
        try:
            resp = await client.post(
                f"{self.api}/chat.postMessage",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"channel": channel, "text": text},
            )
            resp.raise_for_status()
            data = resp.json()
            ok = bool(data.get("ok"))
            log.info("slack.bot.sent", channel=channel, ok=ok)
            return SendResult(success=ok, message_id=str(data.get("ts", "")), provider=self.name)
        finally:
            if owns:
                await client.aclose()


def get_slack_client() -> SlackClient:
    """Retourne le client Slack configuré ; mock si pas de token (keyless)."""
    if settings.slack_provider.lower() == "bot" and settings.slack_bot_token:
        return BotSlackClient()
    if settings.slack_provider.lower() == "bot":
        log.warning("slack.provider.fallback", reason="no token", to="mock")
    return MockSlackClient()
