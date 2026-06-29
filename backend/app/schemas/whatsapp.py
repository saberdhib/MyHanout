"""Schémas WhatsApp (webhook entrant + réponse)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WhatsAppInbound(BaseModel):
    """Message entrant simplifié (le vrai payload Meta est plus riche)."""

    from_: str = Field(default="", alias="from")
    message: str = ""

    model_config = {"populate_by_name": True}


class WhatsAppReply(BaseModel):
    to: str
    reply: str
    agent: str | None = None
    requires_approval: bool = False
    actions: list[dict] = Field(default_factory=list)
