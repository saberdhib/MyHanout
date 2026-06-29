"""Tests RAG (embeddings mock + vector store in-memory, tenant-scopé)."""

import pytest

from app.intelligence.rag.embeddings import MockEmbeddingProvider
from app.intelligence.rag.store import InMemoryVectorStore


def test_embedding_is_deterministic_and_normalized():
    e = MockEmbeddingProvider()
    v1 = e.embed("boeuf haché 25 kg")
    v2 = e.embed("boeuf haché 25 kg")
    assert v1 == v2
    assert len(v1) == e.dim
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_inmemory_store_ranks_and_isolates_tenants():
    store = InMemoryVectorStore()
    e = MockEmbeddingProvider()
    await store.add(
        None,
        organization_id=1,
        invoice_id=1,
        content="facture boeuf haché",
        embedding=e.embed("facture boeuf haché"),
    )
    await store.add(
        None,
        organization_id=1,
        invoice_id=2,
        content="facture farine sucre",
        embedding=e.embed("facture farine sucre"),
    )
    # Org 2 a son propre contenu.
    await store.add(
        None,
        organization_id=2,
        invoice_id=3,
        content="facture lait",
        embedding=e.embed("facture lait"),
    )

    res = await store.search(None, organization_id=1, embedding=e.embed("boeuf"), k=2)
    assert res and res[0].content == "facture boeuf haché"
    # Isolation : org 2 ne voit que son contenu.
    res2 = await store.search(None, organization_id=2, embedding=e.embed("boeuf"), k=5)
    assert all(c.content == "facture lait" for c in res2)


def test_rag_index_and_query_endpoint(client):
    # Indexe la facture seedée (org A) puis interroge.
    idx = client.post("/api/v1/rag/index/invoices/1")
    assert idx.status_code == 200
    assert idx.json()["chunks_indexed"] >= 1

    resp = client.post("/api/v1/rag/query", json={"question": "facture"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert len(data["sources"]) >= 1  # passages cités


def test_rag_query_isolated_for_other_org(org_b_client):
    # Org B n'a rien indexé -> aucune source (isolation du store).
    resp = org_b_client.post("/api/v1/rag/query", json={"question": "facture"})
    assert resp.status_code == 200
    assert resp.json()["sources"] == []
