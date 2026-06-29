"""Vector store : abstraction + implémentation in-memory (défaut) et pgvector.

Isolation tenant : toutes les opérations sont paramétrées par `organization_id`.
- InMemory : défaut local/CI/tests (cosine en Python), sans Postgres.
- PgVector : table `document_chunk` (pgvector). Requêtes SQL brutes -> le filtre
  tenant est appliqué EXPLICITEMENT (le garde-fou ORM ne couvre pas le SQL brut).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


class Chunk(BaseModel):
    content: str
    score: float
    invoice_id: int | None = None


class VectorStore(ABC):
    @abstractmethod
    async def add(
        self,
        session: AsyncSession,
        *,
        organization_id: int,
        invoice_id: int | None,
        content: str,
        embedding: list[float],
    ) -> None: ...

    @abstractmethod
    async def search(
        self, session: AsyncSession, *, organization_id: int, embedding: list[float], k: int
    ) -> list[Chunk]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryVectorStore(VectorStore):
    """Store en mémoire (process), isolé par organisation. Pour local/CI/tests."""

    def __init__(self) -> None:
        # org_id -> list[(content, embedding, invoice_id)]
        self._data: dict[int, list[tuple[str, list[float], int | None]]] = {}

    async def add(self, session, *, organization_id, invoice_id, content, embedding) -> None:
        self._data.setdefault(organization_id, []).append((content, embedding, invoice_id))

    async def search(self, session, *, organization_id, embedding, k) -> list[Chunk]:
        items = self._data.get(organization_id, [])
        scored = [
            Chunk(content=c, score=_cosine(embedding, e), invoice_id=iid) for c, e, iid in items
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]


class PgVectorStore(VectorStore):
    """Store pgvector (table document_chunk). org_id filtré explicitement."""

    async def add(self, session, *, organization_id, invoice_id, content, embedding) -> None:
        vec = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
        await session.execute(
            text(
                "INSERT INTO document_chunk (organization_id, invoice_id, content, embedding) "
                "VALUES (:org, :inv, :content, CAST(:emb AS vector))"
            ),
            {"org": organization_id, "inv": invoice_id, "content": content, "emb": vec},
        )

    async def search(self, session, *, organization_id, embedding, k) -> list[Chunk]:
        vec = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
        rows = await session.execute(
            text(
                "SELECT content, invoice_id, 1 - (embedding <=> CAST(:emb AS vector)) AS score "
                "FROM document_chunk WHERE organization_id = :org "
                "ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :k"
            ),
            {"emb": vec, "org": organization_id, "k": k},
        )
        return [
            Chunk(content=r.content, score=float(r.score), invoice_id=r.invoice_id)
            for r in rows.all()
        ]


_memory_store = InMemoryVectorStore()


def get_vector_store() -> VectorStore:
    if settings.rag_vector_store.lower() == "pgvector":
        return PgVectorStore()
    return _memory_store
