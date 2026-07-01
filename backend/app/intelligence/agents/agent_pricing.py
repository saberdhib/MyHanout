"""Agent Prix — propose des prix conseillés (marge cible + arrondi psychologique)."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class PricingAgent(BaseAgent):
    name = "agent_pricing"
    description = "Propose des prix conseillés selon la marge cible et le marché."
    handled_intents = ("pricing", "prix", "tarif", "marge")

    async def run(self, context: AgentContext) -> AgentResult:
        # `suggestions` : dicts {product_name, current_price, suggested_price, action, explanation}.
        sugg = [s for s in context.data.get("suggestions", []) if s.get("action") != "hold"]
        if not sugg:
            return AgentResult(
                agent=self.name,
                reply="Vos prix tiennent la marge cible : rien à ajuster. 👍",
                explanation="Aucun écart significatif au prix conseillé.",
                confidence=0.6,
            )
        top = sugg[0]
        actions = [
            AgentAction(
                type="apply_price",
                payload={"product": s.get("product_name"), "price": s.get("suggested_price")},
                requires_approval=True,
            )
            for s in sugg[:5]
        ]
        reply = (
            f"{len(sugg)} prix à revoir. Ex. : « {top.get('product_name')} » "
            f"{top.get('current_price')}€ → {top.get('suggested_price')}€. J'ajuste ?"
        )
        return AgentResult(
            agent=self.name,
            reply=reply,
            explanation=top.get("explanation", "Prix conseillé selon marge cible."),
            actions=actions,
            confidence=0.7,
        )
