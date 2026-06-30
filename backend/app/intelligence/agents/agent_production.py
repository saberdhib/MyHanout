"""Agent Production — planification de la fabrication en magasin.

Formate le plan de production (calculé par `production_service`) en réponse lisible
+ actions à valider. Pour boulangerie/traiteur/boucherie-prep.
"""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class ProductionAgent(BaseAgent):
    name = "agent_production"
    description = "Propose le plan de production du jour (combien fabriquer) et les ingrédients."
    handled_intents = ("production", "fabrication", "fournée", "fournee", "produire")

    async def run(self, context: AgentContext) -> AgentResult:
        # `plans` : liste de dicts {product_name, suggested_quantity, batches, explanation}.
        plans = [p for p in context.data.get("plans", []) if p.get("suggested_quantity", 0) > 0]
        if not plans:
            return AgentResult(
                agent=self.name,
                reply="Rien à produire pour l'instant : le stock couvre la demande prévue. 👍",
                explanation="Aucun produit fini sous son besoin prévu.",
                confidence=0.6,
            )

        top = plans[0]
        actions = [
            AgentAction(
                type="confirm_production",
                payload={
                    "product": p.get("product_name"),
                    "quantity": p.get("suggested_quantity"),
                },
                requires_approval=True,
            )
            for p in plans[:5]
        ]
        reply = (
            f"{len(plans)} produit(s) à fabriquer. Ex. : « {top.get('product_name')} » → "
            f"~{top.get('suggested_quantity'):.0f} ({top.get('batches'):.0f} fournée(s)). "
            "Je prépare le plan de production ?"
        )
        return AgentResult(
            agent=self.name,
            reply=reply,
            explanation=top.get("explanation", "Plan dérivé de la prévision de demande."),
            actions=actions,
            confidence=0.7,
        )
