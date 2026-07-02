"""Webhook Slack (Events API) : même machine conversationnelle que WhatsApp/Telegram.

- `url_verification` : répond au challenge d'activation Slack.
- `event_callback` (message d'un humain) : texte → orchestrateur, réponse via le
  client Slack (réel si token, sinon mock). On ignore les messages de bots
  (évite les boucles).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.logging import get_logger
from app.messaging.slack import get_slack_client
from app.services.conversation_service import handle_text

router = APIRouter(prefix="/slack", tags=["slack"])
log = get_logger(__name__)


@router.post("/webhook")
async def slack_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reçoit un event Slack, route le texte et répond dans le canal."""
    payload = await request.json()

    # 1) Handshake d'activation de l'abonnement Events.
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    event = payload.get("event") or {}
    # On ne répond qu'aux messages humains (pas aux messages de bots → anti-boucle).
    if event.get("type") != "message" or event.get("bot_id") or event.get("subtype"):
        return {"ok": True, "skipped": True}

    # Idempotence : Slack re-livre le même event (event_id) sur non-2xx / timeout.
    from app.messaging.idempotency import mark_seen

    if not await mark_seen(session, "slack", payload.get("event_id")):
        return {"ok": True, "skipped": "duplicate"}

    channel = str(event.get("channel", ""))
    text = event.get("text", "")
    if not channel:
        return {"ok": True, "skipped": True}

    reply = await handle_text(session, channel, text)
    await get_slack_client().send_text(channel, reply)
    return {"ok": True, "reply": reply}
