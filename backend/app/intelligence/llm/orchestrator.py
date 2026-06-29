"""Orchestrateur : détecte l'intent et route vers l'agent adéquat.

Détection d'intent par mots-clés en MVP ; remplaçable par une classification
LLM. Le SupportAgent sert de fallback. Toute action sensible passe par le
contrôle de gouvernance (human-in-the-loop).
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.intelligence.agents import (
    AGENT_CLASSES,
    AgentContext,
    AgentResult,
    BaseAgent,
    GovernanceAgent,
    SupportAgent,
)

log = get_logger(__name__)

# Mots-clés -> intent (heuristique simple).
_INTENT_KEYWORDS: dict[str, str] = {
    "command": "order",
    "commande": "order",
    "réassort": "order",
    "reassort": "order",
    "stock": "stock",
    "rupture": "stock",
    "péremption": "stock",
    "facture": "finance",
    "échéance": "finance",
    "echeance": "finance",
    "trésorerie": "finance",
    "promo": "marketing",
    "marketing": "marketing",
    "annonce": "marketing",
}


def detect_intent(message: str) -> str | None:
    """Détection d'intent naïve par mots-clés (MVP)."""
    lowered = message.lower()
    for keyword, intent in _INTENT_KEYWORDS.items():
        if keyword in lowered:
            return intent
    return None


class Orchestrator:
    """Instancie les agents et route les messages entrants."""

    def __init__(self) -> None:
        self.agents: list[BaseAgent] = [cls() for cls in AGENT_CLASSES]
        self.governance = next(
            (a for a in self.agents if isinstance(a, GovernanceAgent)), GovernanceAgent()
        )
        self.fallback = next(
            (a for a in self.agents if isinstance(a, SupportAgent)), SupportAgent()
        )

    def select_agent(self, intent: str | None) -> BaseAgent:
        for agent in self.agents:
            if agent.can_handle(intent):
                return agent
        return self.fallback

    async def handle(self, message: str, *, user_id: int | None = None, data: dict | None = None) -> AgentResult:
        intent = detect_intent(message)
        agent = self.select_agent(intent)
        log.info("orchestrator.route", intent=intent, agent=agent.name)

        context = AgentContext(
            intent=intent, message=message, user_id=user_id, data=data or {}
        )
        result = await agent.run(context)

        # Contrôle de gouvernance des actions proposées (human-in-the-loop).
        for action in result.actions:
            allowed, reason = self.governance.review_action(action)
            action.requires_approval = action.requires_approval or not allowed
            log.info(
                "orchestrator.governance",
                action=action.type,
                auto_allowed=allowed,
                reason=reason,
            )
        return result


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Singleton léger d'orchestrateur."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
