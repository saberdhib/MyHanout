"""Engine et session SQLAlchemy async."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.core.tenancy  # noqa: F401  (installe les events du garde-fou tenant)
from app.config import settings

engine = create_async_engine(
    settings.sqlalchemy_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : fournit une session et la ferme proprement.

    Réinitialise le GUC RLS (`app.current_org` → vide) en début de requête : une
    connexion recyclée du pool ne doit pas hériter du tenant d'une requête précédente.
    L'auth (get_current_user / clé API / plateforme) posera ensuite l'org réelle.
    """
    from app.core.rls import set_session_org

    async with AsyncSessionLocal() as session:
        try:
            await set_session_org(session, None)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
