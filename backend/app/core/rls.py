"""Row-Level Security Postgres (defense-in-depth du multi-tenant).

Le garde-fou applicatif (`app.core.tenancy`) filtre déjà les SELECT ORM. La RLS ajoute
une **seconde barrière au niveau base** : même une requête SQL brute ou un bug de code
ne peut pas franchir l'isolation tenant. Les policies (migration `0025`) comparent
`organization_id` au GUC de session `app.current_org` :

- GUC = id d'org  → seules les lignes de cette org sont visibles/insérables.
- GUC vide/NULL   → accès complet (plan **plateforme**, seed, workers) — miroir du
  comportement `current_org=None` du garde-fou applicatif.

`set_session_org` pose ce GUC sur la connexion de la requête. No-op hors PostgreSQL
(sqlite de test n'a pas de RLS) → aucun impact sur la suite mock.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_session_org(session: AsyncSession, org_id: int | None) -> None:
    """Pose `app.current_org` sur la connexion courante (PostgreSQL uniquement).

    `set_config(..., is_local => false)` = niveau session : survit aux commits pendant
    la durée de vie de la connexion (réinitialisé en début de requête, cf. get_session).
    """
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    await session.execute(
        text("SELECT set_config('app.current_org', :v, false)"),
        {"v": "" if org_id is None else str(org_id)},
    )
