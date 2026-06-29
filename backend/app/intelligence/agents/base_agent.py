"""Interface commune à tous les agents IA (human-in-the-loop & explicabilité)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.intelligence.llm import LLMProvider, get_llm_provider


class AgentContext(BaseModel):
    """Entrée d'un agent : message utilisateur + métadonnées."""

    intent: str | None = None
    message: str = ""
    user_id: int | None = None
    # Données contextuelles libres (produit, fournisseur, etc.).
    data: dict = Field(default_factory=dict)


class AgentAction(BaseModel):
    """Action proposée par un agent (peut nécessiter validation humaine)."""

    type: str  # ex: "create_order", "send_alert", "none"
    payload: dict = Field(default_factory=dict)
    requires_approval: bool = True


class AgentResult(BaseModel):
    """Sortie standard d'un agent."""

    agent: str
    reply: str
    # Explicabilité : pourquoi l'agent répond/agit ainsi.
    explanation: str | None = None
    actions: list[AgentAction] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class BaseAgent(ABC):
    """Contrat commun. Chaque agent déclare son `name` et ses intents gérés."""

    name: str = "base"
    description: str = ""
    handled_intents: tuple[str, ...] = ()

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()

    def can_handle(self, intent: str | None) -> bool:
        return bool(intent) and intent in self.handled_intents

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Traite la demande et renvoie un résultat (réponse + actions)."""
        raise NotImplementedError
