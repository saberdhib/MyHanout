"""Endpoints WhatsApp : vérification du webhook + réception des messages."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response

from app.core.logging import get_logger
from app.messaging.whatsapp.webhook import verify_subscription
from app.schemas.whatsapp import WhatsAppInbound, WhatsAppReply
from app.services.whatsapp_service import handle_inbound

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


@router.post("/webhook", response_model=WhatsAppReply)
async def receive_webhook(request: Request) -> WhatsAppReply:
    """Reçoit un message, l'écho + le route vers l'orchestrateur d'agents.

    Accepte un payload simplifié {from, message}. Le vrai payload Meta
    (entry/changes/messages) sera mappé ici lors de l'intégration réelle.
    """
    body = await request.json()
    inbound = WhatsAppInbound.model_validate(body)
    log.info("whatsapp.inbound", **inbound.model_dump(by_alias=True))
    return await handle_inbound(inbound)
