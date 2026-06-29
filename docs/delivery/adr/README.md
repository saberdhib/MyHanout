# Architecture Decision Records (ADR)

Décisions structurantes de MyHanout AI, format léger (contexte / décision / conséquences).

| ADR | Décision |
|-----|----------|
| [0001](0001-async-sqlalchemy.md) | SQLAlchemy 2.0 **async** (asyncpg) |
| [0002](0002-provider-abstraction-mock-first.md) | Providers externes **abstraits + mock par défaut** |
| [0003](0003-naive-default-forecasting.md) | Modèle de forecasting **naïf par défaut** |
| [0004](0004-central-tenant-guard.md) | **Garde-fou tenant central** (events ORM) |
| [0005](0005-human-in-the-loop.md) | **Human-in-the-loop** sur les actions sortantes |
