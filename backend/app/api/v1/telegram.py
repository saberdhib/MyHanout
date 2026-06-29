"""Webhook Telegram : même machine conversationnelle que WhatsApp.

Vérifie le secret d'en-tête Telegram (X-Telegram-Bot-Api-Secret-Token) si
configuré. Texte → orchestrateur/état ; photo → pipeline OCR. Réponses via le
client Telegram (réel si token, sinon mock).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_db
from app.core.logging import get_logger
from app.messaging.telegram import get_telegram_client
from app.services.conversation_service import handle_text, ingest_invoice_bytes

router = APIRouter(prefix="/telegram", tags=["telegram"])
log = get_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Reçoit une update Telegram, route (texte/photo) et répond."""
    if settings.telegram_webhook_secret and (
        x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        log.warning("telegram.webhook.bad_secret")
        return Response(status_code=403, content="invalid secret")  # type: ignore[return-value]

    update = await request.json()
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    if not chat_id:
        return {"ok": True, "skipped": True}

    client = get_telegram_client()
    if message.get("photo"):
        file_id = message["photo"][-1]["file_id"]  # plus grande résolution
        content = await client.download_media(file_id)
        reply = await ingest_invoice_bytes(
            session, chat_id, content, filename=f"telegram-{file_id}.jpg"
        )
    else:
        reply = await handle_text(session, chat_id, message.get("text", ""))

    await client.send_text(chat_id, reply)
    return {"ok": True, "reply": reply}
