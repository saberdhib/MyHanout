"""Crée le schéma via `Base.metadata` (dev / E2E sur sqlite, sans migrations).

Les migrations Alembic restent la source de vérité en prod (Postgres + pgvector).
Mais sur sqlite (tests, E2E), les colonnes `vector` n'existent pas : on crée donc
le schéma directement depuis les modèles ORM, comme le fait la suite de tests.

Usage : `python -m app.db.create_all`
"""

from __future__ import annotations

import asyncio

import app.models as models  # noqa: F401 — enregistre toutes les tables sur Base.metadata
from app.db.base import Base
from app.db.session import engine


async def create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_all())
