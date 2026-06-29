# ADR 0001 — SQLAlchemy 2.0 async (asyncpg)

**Statut** : accepté · **Date** : 2026-06

## Contexte
API FastAPI (async). Besoin d'un ORM moderne, typé, compatible Postgres + pgvector.

## Décision
SQLAlchemy 2.0 en mode **async** (`AsyncSession`, driver `asyncpg`), migrations Alembic
en mode async. Tests rapides sur SQLite (`aiosqlite`) ; intégration sur Postgres réel.

## Conséquences
- ➕ Cohérence avec FastAPI, scaling I/O, typage `Mapped[...]`.
- ➕ Le garde-fou tenant s'appuie sur les events de session (`do_orm_execute`, `before_flush`).
- ➖ Pièges async (lazy-load → `MissingGreenlet`) : on charge explicitement les relations
  (`selectinload`/`refresh`).
- ➖ pgvector hors ORM (SQL brut) pour préserver la compat SQLite des tests.
