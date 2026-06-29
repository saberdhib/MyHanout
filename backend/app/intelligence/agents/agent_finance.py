"""Agent finance — échéances fournisseurs et cashflow."""

from __future__ import annotations

from app.intelligence.agents.base_agent import AgentContext, AgentResult, BaseAgent


class FinanceAgent(BaseAgent):
    name = "agent_finance"
    description = "Suit les échéances de factures et estime la trésorerie."
    handled_intents = ("finance", "cashflow", "echeance", "facture", "tresorerie")

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            reply="Voici les échéances à venir et l'impact sur la trésorerie.",
            explanation="Basé sur les factures non payées et leurs dates d'échéance.",
            confidence=0.5,
        )
