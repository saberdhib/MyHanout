"""Interface abstraite des providers LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    # Usage tokens éventuel (prompt/completion) pour l'observabilité.
    usage: dict = Field(default_factory=dict)


class LLMProvider(ABC):
    """Contrat commun (Mistral, Claude, mock)."""

    name: str = "abstract"

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Génère une complétion à partir d'une liste de messages."""
        raise NotImplementedError
