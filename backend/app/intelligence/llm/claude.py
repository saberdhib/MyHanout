"""Provider LLM Claude / Anthropic (stub).

Squelette d'intégration via l'API Messages d'Anthropic. Sans clé, erreur
explicite — utiliser LLM_PROVIDER=mock en local.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.llm.base import LLMMessage, LLMProvider, LLMResponse

log = get_logger(__name__)


class ClaudeLLMProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.llm_model
        self.endpoint = "https://api.anthropic.com/v1/messages"

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY manquante. Utilisez LLM_PROVIDER=mock en local.")
        system = "\n".join(m.content for m in messages if m.role == "system")
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": chat,
        }
        async with httpx.AsyncClient(timeout=60) as client:  # pragma: no cover
            resp = await client.post(
                self.endpoint,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        return LLMResponse(
            content=text, model=self.model, provider=self.name, usage=data.get("usage", {})
        )
