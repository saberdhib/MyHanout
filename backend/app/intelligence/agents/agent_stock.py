"""Agent stock — ruptures et péremptions."""

from __future__ import annotations

from app.intelligence.agents.base_agent import AgentContext, AgentResult, BaseAgent


class StockAgent(BaseAgent):
    name = "agent_stock"
    description = "Surveille les ruptures de stock et les péremptions proches."
    handled_intents = ("stock", "rupture", "peremption", "inventory")

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            reply="Voici l'état des stocks à risque (rupture/péremption).",
            explanation="Analyse des seuils de réassort et des dates de péremption.",
            confidence=0.5,
        )
