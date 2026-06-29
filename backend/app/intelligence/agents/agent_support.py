"""Agent support — Q&A métier (fallback conversationnel)."""

from __future__ import annotations

from app.intelligence.agents.base_agent import (
    AgentContext,
    AgentResult,
    BaseAgent,
)
from app.intelligence.llm import LLMMessage


class SupportAgent(BaseAgent):
    name = "agent_support"
    description = "Répond aux questions métier générales (fallback)."
    handled_intents = ("support", "question", "aide", "help")

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self.llm.complete(
            [
                LLMMessage(role="system", content="Tu es le support métier de MyHanout AI."),
                LLMMessage(role="user", content=context.message or ""),
            ]
        )
        return AgentResult(
            agent=self.name,
            reply=response.content,
            explanation="Réponse conversationnelle (fallback support).",
            confidence=0.4,
        )
