"""Helpers webhook WhatsApp : handshake, signature Meta, parsing des messages."""

from __future__ import annotations

import hashlib
import hmac

from pydantic import BaseModel

from app.config import settings


def verify_subscription(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """Valide le handshake GET de Meta. Renvoie le challenge si OK, sinon None."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return challenge
    return None


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Vérifie X-Hub-Signature-256 (HMAC-SHA256 du corps brut avec l'app secret).

    Si aucun app secret n'est configuré (local/CI mock), la vérification est
    désactivée et renvoie True — le défaut sans clé reste fonctionnel.
    """
    if not settings.whatsapp_app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


class InboundMessage(BaseModel):
    from_: str
    type: str  # "text" | "image"
    text: str | None = None
    media_id: str | None = None
    # Identifiant du message côté fournisseur (wamid…) — pour l'idempotence.
    external_id: str | None = None


def parse_incoming(payload: dict) -> list[InboundMessage]:
    """Extrait les messages d'un payload (format Meta OU format simplifié).

    Format Meta : entry[].changes[].value.messages[].
    Format simplifié (tests/local) : {"from": ..., "message": ...} ou
    {"from": ..., "image_id": ...}.
    """
    messages: list[InboundMessage] = []

    if "entry" in payload:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    sender = msg.get("from", "")
                    mtype = msg.get("type", "text")
                    ext_id = msg.get("id")
                    if mtype == "text":
                        messages.append(
                            InboundMessage(
                                from_=sender,
                                type="text",
                                text=msg.get("text", {}).get("body", ""),
                                external_id=ext_id,
                            )
                        )
                    elif mtype == "image":
                        messages.append(
                            InboundMessage(
                                from_=sender,
                                type="image",
                                media_id=msg.get("image", {}).get("id"),
                                external_id=ext_id,
                            )
                        )
        return messages

    # Format simplifié.
    sender = payload.get("from", "")
    ext_id = payload.get("id")
    if payload.get("image_id"):
        messages.append(
            InboundMessage(
                from_=sender, type="image", media_id=payload["image_id"], external_id=ext_id
            )
        )
    elif payload.get("message") is not None:
        messages.append(
            InboundMessage(from_=sender, type="text", text=payload["message"], external_id=ext_id)
        )
    return messages
