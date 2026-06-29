"""LLM : sélection du provider configuré + types publics."""

from app.config import settings
from app.intelligence.llm.base import LLMMessage, LLMProvider, LLMResponse


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """Retourne le provider LLM configuré (cf. LLM_PROVIDER)."""
    provider = (name or settings.llm_provider).lower()
    if provider == "claude":
        from app.intelligence.llm.claude import ClaudeLLMProvider

        return ClaudeLLMProvider()
    if provider == "mistral":
        from app.intelligence.llm.mistral import MistralLLMProvider

        return MistralLLMProvider()
    if provider == "huggingface" and settings.huggingface_api_key:
        from app.intelligence.llm.huggingface import HuggingFaceLLMProvider

        return HuggingFaceLLMProvider()
    from app.intelligence.llm.mock import MockLLMProvider

    return MockLLMProvider()


__all__ = ["LLMMessage", "LLMProvider", "LLMResponse", "get_llm_provider"]
