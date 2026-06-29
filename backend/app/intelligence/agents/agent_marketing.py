"""Agent marketing — génération de contenu (promos, messages clients)."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
)
from app.intelligence.llm import LLMMessage


class MarketingAgent(BaseAgent):
    name = "agent_marketing"
    description = "Génère du contenu marketing (promotions, annonces) via le LLM."
    handled_intents = ("marketing", "promo", "contenu", "annonce")

    async def run(self, context: AgentContext) -> AgentResult:
        # Démonstration d'usage du LLM (mock par défaut).
        response = await self.llm.complete(
            [
                LLMMessage(
                    role="system",
                    content="Tu es un assistant marketing pour un commerce de proximité.",
                ),
                LLMMessage(role="user", content=context.message or "Propose une promo."),
            ]
        )
        return AgentResult(
            agent=self.name,
            reply=response.content,
            explanation=f"Contenu généré via le provider LLM « {response.provider} ».",
            confidence=0.5,
        )
