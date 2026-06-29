"""Provider LLM HuggingFace (Inference API). Sans clé → erreur explicite (la
fabrique retombe alors sur le mock)."""

from __future__ import annotations

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.llm.base import LLMMessage, LLMProvider, LLMResponse

log = get_logger(__name__)


class HuggingFaceLLMProvider(LLMProvider):
    name = "huggingface"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_llm_model
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model}"

    @staticmethod
    def _to_prompt(messages: list[LLMMessage]) -> str:
        parts = []
        for m in messages:
            tag = {"system": "[SYS]", "user": "[USER]", "assistant": "[ASSISTANT]"}.get(m.role, "")
            parts.append(f"{tag} {m.content}")
        parts.append("[ASSISTANT]")
        return "\n".join(parts)

    async def complete(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 1024
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("HUGGINGFACE_API_KEY manquante. Utilisez LLM_PROVIDER=mock.")
        payload = {
            "inputs": self._to_prompt(messages),
            "parameters": {
                "temperature": max(0.01, temperature),
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:  # pragma: no cover
            resp = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        text = data[0].get("generated_text", "") if isinstance(data, list) else str(data)
        return LLMResponse(content=text.strip(), model=self.model, provider=self.name)
