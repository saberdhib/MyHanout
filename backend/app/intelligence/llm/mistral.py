"""Provider LLM Mistral (stub).

Squelette d'intégration via l'API chat de Mistral. Sans clé, erreur explicite.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.intelligence.llm.base import LLMMessage, LLMProvider, LLMResponse


class MistralLLMProvider(LLMProvider):
    name = "mistral"

    def __init__(self, api_key: str | None = None, model: str = "mistral-large-latest") -> None:
        self.api_key = api_key or settings.mistral_api_key
        self.model = model
        self.endpoint = "https://api.mistral.ai/v1/chat/completions"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY manquante. Utilisez LLM_PROVIDER=mock en local."
            )
        payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        async with httpx.AsyncClient(timeout=60) as client:  # pragma: no cover
            resp = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(
            content=text, model=self.model, provider=self.name, usage=data.get("usage", {})
        )
