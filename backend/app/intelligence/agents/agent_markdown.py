"""Agent Démarque — anti-gaspillage frais.

Transforme les suggestions de démarque (calculées par `markdown_service`) en une
réponse lisible + des actions à valider (human-in-the-loop). Le calcul lourd vit
dans le service ; l'agent se charge du dialogue et de proposer l'action.
"""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)


class MarkdownAgent(BaseAgent):
    name = "agent_markdown"
    description = "Propose des démarques pour écouler le frais avant péremption (anti-gaspi)."
    handled_intents = ("markdown", "démarque", "demarque", "gaspillage", "péremption")

    async def run(self, context: AgentContext) -> AgentResult:
        # `markdowns` : liste de dicts {product_name, discount_pct, suggested_price,
        # recovered_value, baseline_loss, explanation} fournie par l'appelant/cycle.
        markdowns = context.data.get("markdowns", [])
        if not markdowns:
            return AgentResult(
                agent=self.name,
                reply="Aucun lot frais à risque pour l'instant : rien à démarquer. 👍",
                explanation="Aucun périssable proche de la péremption avec invendu prévu.",
                confidence=0.6,
            )

        top = markdowns[0]
        actions = [
            AgentAction(
                type="apply_markdown",
                payload={
                    "product": m.get("product_name"),
                    "discount_pct": m.get("discount_pct"),
                    "suggested_price": m.get("suggested_price"),
                },
                requires_approval=True,  # toujours validé par un humain
            )
            for m in markdowns[:5]
        ]
        recovered = sum(float(m.get("recovered_value", 0)) for m in markdowns)
        reply = (
            f"{len(markdowns)} lot(s) frais à risque. Ex. : « {top.get('product_name')} » → "
            f"-{top.get('discount_pct')}% (prix {top.get('suggested_price')}€). "
            f"Valeur récupérable totale ~{recovered:.0f}€. Je prépare les démarques ?"
        )
        return AgentResult(
            agent=self.name,
            reply=reply,
            explanation=top.get("explanation", "Démarque calculée selon péremption & écoulement."),
            actions=actions,
            confidence=0.7,
        )
