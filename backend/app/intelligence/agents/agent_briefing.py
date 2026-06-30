"""Agent Tâches du jour — consolide les autres agents en un briefing priorisé.

Au cœur de l'orchestration proactive : c'est lui qui transforme la collection
d'agents en une *liste d'actions du jour* lisible. Le calcul vit dans
`briefing_service` ; l'agent porte le dialogue.
"""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
)


class BriefingAgent(BaseAgent):
    name = "agent_briefing"
    description = "Prépare le briefing du matin : les actions du jour, priorisées."
    handled_intents = ("briefing", "tâches", "taches", "journée", "journee", "matin")

    async def run(self, context: AgentContext) -> AgentResult:
        summary = context.data.get("summary")
        items = context.data.get("items", [])
        if not items:
            return AgentResult(
                agent=self.name,
                reply="Rien d'urgent aujourd'hui : pas d'action prioritaire. Bonne journée ! ☀️",
                explanation="Aucune alerte/réassort/démarque/production en attente.",
                confidence=0.6,
            )
        top = "\n".join(f"• {it.get('title')}" for it in items[:5])
        return AgentResult(
            agent=self.name,
            reply=f"Voici votre briefing du matin — {summary}\n{top}",
            explanation="Consolidation priorisée des alertes, réassort, démarques et production.",
            confidence=0.75,
        )
