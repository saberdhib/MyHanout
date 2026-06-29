"""Helpers de vérification du webhook WhatsApp (handshake Meta)."""

from __future__ import annotations

from app.config import settings


def verify_subscription(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """Valide le handshake GET de Meta. Renvoie le challenge si OK, sinon None."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return challenge
    return None
