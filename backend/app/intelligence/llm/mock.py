"""Provider LLM mock — déterministe, sans appel réseau (défaut local/CI)."""

from __future__ import annotations

from app.intelligence.llm.base import LLMMessage, LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        content = f"[mock-llm] J'ai bien reçu : « {last_user[:200]} »."
        return LLMResponse(
            content=content,
            model="mock-1",
            provider=self.name,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )
