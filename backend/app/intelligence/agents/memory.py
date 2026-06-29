"""Mémoire d'agent : persistance et rappel des tours récents (tenant-scopé)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory


class MemoryStore:
    """Lecture/écriture de la mémoire conversationnelle d'un agent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def remember(self, *, agent: str, subject: str, role: str, content: str) -> None:
        # organization_id estampillé automatiquement par le garde-fou tenant.
        self.session.add(AgentMemory(agent=agent, subject=subject, role=role, content=content))
        await self.session.flush()

    async def recall(self, *, agent: str, subject: str, limit: int = 10) -> list[dict]:
        """Retourne les `limit` derniers tours (ordre chronologique)."""
        rows = await self.session.scalars(
            select(AgentMemory)
            .where(AgentMemory.agent == agent, AgentMemory.subject == subject)
            .order_by(AgentMemory.id.desc())
            .limit(limit)
        )
        turns = [{"role": r.role, "content": r.content} for r in rows.all()]
        return list(reversed(turns))
