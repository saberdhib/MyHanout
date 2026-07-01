"""Agent Effectifs — conseille le personnel selon l'affluence prévue."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
)


class StaffingAgent(BaseAgent):
    name = "agent_staffing"
    description = "Conseille les effectifs selon l'affluence prévue (pics = renfort)."
    handled_intents = ("staffing", "effectif", "personnel", "planning", "equipe", "équipe")

    async def run(self, context: AgentContext) -> AgentResult:
        # `days` : dicts {date, weekday, delta, suggested_staff, explanation}.
        peaks = [d for d in context.data.get("days", []) if d.get("delta", 0) > 0]
        if not peaks:
            return AgentResult(
                agent=self.name,
                reply="Affluence régulière sur la période : effectif de base suffisant. 👍",
                explanation="Aucun jour de pic détecté sur l'horizon.",
                confidence=0.6,
            )
        top = peaks[0]
        reply = (
            f"{len(peaks)} jour(s) de pic à renforcer. Ex. : {top.get('weekday')} "
            f"→ +{top.get('delta')} personne(s) ({top.get('suggested_staff')} au total)."
        )
        return AgentResult(
            agent=self.name,
            reply=reply,
            explanation=top.get("explanation", "Renfort dérivé de l'affluence prévue."),
            confidence=0.7,
        )
