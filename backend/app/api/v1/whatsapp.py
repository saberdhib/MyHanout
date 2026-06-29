"""Endpoints WhatsApp : vérification du webhook + réception (texte + image)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.logging import get_logger
from app.messaging.whatsapp import get_whatsapp_client
from app.messaging.whatsapp.webhook import (
    parse_incoming,
    verify_signature,
    verify_subscription,
)
from app.services.conversation_service import handle_image, handle_text

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
log = get_logger(__name__)


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    """Handshake de vérification Meta (renvoie le challenge si le token est valide)."""
    challenge = verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        return Response(status_code=403, content="forbidden")
    return Response(status_code=200, content=challenge)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict:
    """Reçoit les messages (texte + image), vérifie la signature, route et répond.

    Texte -> machine à états de conversation ; image -> pipeline OCR (Phase 1).
    Les réponses sont renvoyées au commerçant via le provider (mock par défaut).
    """
    raw = await request.body()
    if not verify_signature(raw, x_hub_signature_256):
        log.warning("whatsapp.webhook.bad_signature")
        return Response(status_code=403, content="invalid signature")  # type: ignore[return-value]

    payload = await request.json()
    messages = parse_incoming(payload)
    client = get_whatsapp_client()
    replies: list[dict] = []

    for msg in messages:
        if msg.type == "image" and msg.media_id:
            reply = await handle_image(session, msg.from_, msg.media_id)
        else:
            reply = await handle_text(session, msg.from_, msg.text or "")
        if msg.from_:
            await client.send_text(msg.from_, reply)
        replies.append({"to": msg.from_, "reply": reply})

    return {"received": len(messages), "replies": replies}
