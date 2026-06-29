"""Tests de l'orchestrateur d'agents et de la gouvernance."""

import pytest

from app.intelligence.llm.orchestrator import detect_intent, get_orchestrator


def test_detect_intent():
    assert detect_intent("je veux une commande") == "order"
    assert detect_intent("rupture de stock") == "stock"
    assert detect_intent("bonjour") is None


@pytest.mark.asyncio
async def test_order_agent_requires_approval():
    orch = get_orchestrator()
    result = await orch.handle("passer une commande de boeuf")
    assert result.agent == "agent_order"
    assert result.actions
    assert all(a.requires_approval for a in result.actions)


@pytest.mark.asyncio
async def test_fallback_to_support():
    orch = get_orchestrator()
    result = await orch.handle("bonjour, une question")
    assert result.agent == "agent_support"
