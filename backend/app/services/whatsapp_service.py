"""Service WhatsApp : relie le webhook à l'orchestrateur d'agents."""

from __future__ import annotations

from app.intelligence.llm.orchestrator import get_orchestrator
from app.schemas.whatsapp import WhatsAppInbound, WhatsAppReply


async def handle_inbound(inbound: WhatsAppInbound) -> WhatsAppReply:
    """Traite un message entrant et renvoie la réponse de l'agent routé."""
    orchestrator = get_orchestrator()
    result = await orchestrator.handle(inbound.message)
    requires_approval = any(a.requires_approval for a in result.actions)
    return WhatsAppReply(
        to=inbound.from_,
        reply=result.reply,
        agent=result.agent,
        requires_approval=requires_approval,
        actions=[a.model_dump() for a in result.actions],
    )
