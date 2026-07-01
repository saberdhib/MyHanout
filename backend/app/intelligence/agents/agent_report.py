"""Agent Bilan — synthétise la semaine écoulée en points clés + actions."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
)


class ReportAgent(BaseAgent):
    name = "agent_report"
    description = "Produit le bilan hebdomadaire (CA, marge, top ventes) et 3 actions."
    handled_intents = ("bilan", "rapport", "resume", "résumé", "semaine", "hebdo")

    async def run(self, context: AgentContext) -> AgentResult:
        report = context.data.get("report")
        if not report:
            return AgentResult(
                agent=self.name,
                reply="Je peux préparer le bilan de la semaine (CA, marge, actions). On y va ?",
                explanation="Bilan hebdomadaire consolidé à la demande.",
                confidence=0.6,
            )
        highlights = "\n".join(f"• {h}" for h in report.get("highlights", [])[:4])
        return AgentResult(
            agent=self.name,
            reply=f"{report.get('narrative', '')}\n{highlights}",
            explanation="Consolidation de la semaine : ventes, marges, alertes, démarque.",
            confidence=0.75,
        )
