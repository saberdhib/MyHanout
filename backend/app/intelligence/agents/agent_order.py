"""Agent commande / réassort — propose des commandes (action sensible)."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class OrderAgent(BaseAgent):
    name = "agent_order"
    description = "Propose des commandes de réassort à partir des stocks et prévisions."
    handled_intents = ("order", "reorder", "commande", "reassort")

    async def run(self, context: AgentContext) -> AgentResult:
        # Stub : propose une commande à valider (human-in-the-loop).
        product = context.data.get("product")
        suggested_qty = context.data.get("suggested_qty", 0)
        action = AgentAction(
            type="create_order",
            payload={"product": product, "quantity": suggested_qty},
            requires_approval=True,  # toujours validé par un humain
        )
        return AgentResult(
            agent=self.name,
            reply=f"Je propose de commander {suggested_qty} de « {product} ». Validez-vous ?",
            explanation="Suggestion basée sur le stock courant et la prévision de demande.",
            actions=[action],
            confidence=0.6,
        )
