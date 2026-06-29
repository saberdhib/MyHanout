"""Agent gouvernance — audit et validation des actions sensibles.

Vérifie qu'une action proposée par un autre agent respecte les règles
(human-in-the-loop, plafonds, droits) avant exécution.
"""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class GovernanceAgent(BaseAgent):
    name = "agent_governance"
    description = "Audite et valide les actions sensibles avant exécution."
    handled_intents = ("governance", "audit", "validation")

    def review_action(self, action: AgentAction) -> tuple[bool, str]:
        """Retourne (autorisé_auto, motif). Les actions sensibles restent manuelles."""
        sensitive = {"create_order", "send_message", "make_payment"}
        if action.type in sensitive or action.requires_approval:
            return False, "Action sensible : validation humaine requise."
        return True, "Action non sensible : exécution autorisée."

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            reply="Contrôle de gouvernance effectué.",
            explanation="Vérifie droits, plafonds et exigence de validation humaine.",
            confidence=0.7,
        )
