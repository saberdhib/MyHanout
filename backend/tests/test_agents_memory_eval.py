"""Tests mémoire d'agent (tenant-scopée) + évaluation du routage."""

import pytest
from sqlalchemy import select

from app.core.tenancy import tenant_context
from app.intelligence.agents.evaluation import evaluate_routing
from app.intelligence.agents.memory import MemoryStore
from app.models.organization import Organization
from tests.conftest import TestSession


def test_routing_eval_accuracy():
    report = evaluate_routing()
    assert report.total == 10
    # Le golden set doit être routé correctement (heuristique mots-clés).
    assert report.accuracy >= 0.9
    assert all(isinstance(c.ok, bool) for c in report.cases)


def test_agents_eval_endpoint(client):
    resp = client.get("/api/v1/agents/eval")
    assert resp.status_code == 200
    assert resp.json()["accuracy"] >= 0.9


@pytest.mark.asyncio
async def test_memory_remember_recall_is_tenant_scoped():
    async with TestSession() as s:
        org_a = await s.scalar(select(Organization).where(Organization.slug == "org-a"))
        org_b = await s.scalar(select(Organization).where(Organization.slug == "org-b"))

        with tenant_context(org_a.id):
            mem = MemoryStore(s)
            await mem.remember(
                agent="agent_support", subject="+111", role="user", content="bonjour"
            )
            await mem.remember(
                agent="agent_support", subject="+111", role="assistant", content="salut"
            )
            turns = await mem.recall(agent="agent_support", subject="+111")
            assert [t["role"] for t in turns] == ["user", "assistant"]
            assert turns[0]["content"] == "bonjour"

        # Org B ne voit pas la mémoire de l'org A (isolation).
        with tenant_context(org_b.id):
            assert await MemoryStore(s).recall(agent="agent_support", subject="+111") == []
        await s.rollback()


def test_whatsapp_fallback_uses_memory(anon_client):
    # Un message générique passe par le fallback (mémoire écrite).
    phone = "+212600009999"
    r = anon_client.post("/api/v1/whatsapp/webhook", json={"from": phone, "message": "bonjour"})
    assert r.status_code == 200
    assert r.json()["replies"][0]["reply"]
