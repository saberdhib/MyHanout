# CLAUDE.md — Guide de contribution (agents & humains)

Ce fichier oriente toute personne (ou IA) qui code sur **MyHanout AI**. Lis-le avant
de modifier le repo. Il capture l'architecture, les conventions et les **pièges réels**
rencontrés.

## 1. Le produit en une phrase
Copilot IA pour commerces de proximité, opéré via **WhatsApp/Telegram + dashboard** :
OCR de factures, prévision de demande, suggestions de réassort explicables, promos
anti-gaspillage — **multi-tenant, human-in-the-loop, RGPD, explicable**.

## 2. Stack & commandes
- **Backend** : Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 **async** (asyncpg),
  Alembic, Celery/Redis, PostgreSQL 16 + **pgvector**.
- **Frontend** : React + Vite + TypeScript + Tailwind (dark mode).
- **Qualité** : `ruff`, `black`, `mypy`, `pytest`. **Le gate doit rester vert à chaque commit.**

```bash
make up            # docker compose (pg+pgvector, redis, api, worker, frontend)
make seed          # données démo (org "demo" : owner + comptable + produits + 1 périssable en fin de vie)
make check         # ruff + mypy + pytest
make migrate       # alembic upgrade head
# Frontend : cd frontend && npx tsc --noEmit
```
Tests : `python3 -m pytest` (sqlite en mémoire, rapide). Intégration pg : marqueur
`integration` (job CI dédié + `INTEGRATION_DATABASE_URL`).

## 3. Architecture en 4 couches (à respecter)
```
ingestion/      OCR (mistral/pdf/mock) -> parsing -> validation -> ETL
data/           models SQLAlchemy (TenantMixin), repositories, migrations, seed
intelligence/   forecasting (naive/prophet/lgbm), agents (+ orchestrateur), llm, rag, signals
applicative/    api/v1 (routers), messaging (whatsapp/telegram/publish), workers, frontend
```
Le **tenant courant** vient du token (cf. §5). Toute dépendance externe est **abstraite +
mockable** (§4).

## 4. Providers : abstraction + mock par défaut (RÈGLE D'OR)
Chaque intégration externe a une interface ABC + une impl **mock par défaut, keyless** :
- `OCRProvider` (mock | mistral | pdf_fallback) — `ingestion/ocr/`
- `LLMProvider` (mock | claude | mistral | **huggingface**) — `intelligence/llm/`
- `EmbeddingProvider` + `VectorStore` (memory | pgvector) — `intelligence/rag/`
- `WhatsAppClient` (mock | business) — `messaging/whatsapp/`
- `TelegramClient` (mock | bot) — `messaging/telegram.py`
- `PublishChannel` (social | customers) — `messaging/publish.py`
- `ForecastModel` (naive | prophet | lgbm) — `intelligence/forecasting/`

**Sans clé → fallback mock.** Le défaut local/CI ne nécessite AUCUNE clé. Pour activer
le réel : variables d'env (cf. `docs/DEPLOY.md`). Quand tu ajoutes un provider : nouvelle
impl derrière l'ABC + branchement dans la fabrique + fallback mock + test avec client HTTP mocké.

## 5. Multi-tenant : garde-fou central (SÉCURITÉ — ne pas contourner)
`app/core/tenancy.py` :
- `organization_id` courant dans un **ContextVar**, posé **uniquement** par `get_current_user`
  depuis le claim `org` du JWT (jamais d'un param client).
- Event `do_orm_execute` → `with_loader_criteria(TenantMixin, …)` : filtre **tous** les
  SELECT ORM (y compris `session.get`, jointures).
- Event `before_flush` : estampille `organization_id` sur les INSERT.
- Modèles métier héritent de `TenantMixin` (product, stock, sale, supplier, invoice, order,
  daily_entry, forecast_evaluation, customer, promo_campaign, agent_memory, document_chunk).
- **Limite** : le SQL brut (hors ORM) n'est PAS filtré → filtrer l'org explicitement
  (cf. `PgVectorStore`). Test d'isolation : `tests/test_tenancy.py` (A ≠ B).

## 6. Pièges réels (déjà rencontrés — évite-les)
- **Async lazy-load** : accéder à une relation non chargée lève `MissingGreenlet`.
  Charger explicitement (`selectinload` / `session.refresh(obj, ["lines"])`) avant sérialisation.
- **`tenant_context` + commit** : le `before_flush` estampille au flush. Mets le
  `commit()` **dans** le `with tenant_context(org):` sinon les inserts différés (ventes,
  factures) partent avec `organization_id NULL`. (Bug vu dans le seed et les tests.)
- **pgvector vs sqlite** : `document_chunk(embedding vector)` n'existe que sur pg (SQL brut
  dans la migration). Les tests tournent sur sqlite via `create_all` (pas les migrations) —
  garder les colonnes vector hors ORM. RAG par défaut = store **memory** (testable sqlite).
- **Migrations** : chaîne **linéaire** (down_revision). Lors d'un merge de branches sœurs,
  re-chaîner (ex. `0003_multitenant` → `0003_phase2_loop`). Toujours réversible (testé down/up).
- **Enums** : `StrEnum` + `values_callable` → stockés en minuscules (cohérent migration/seed).
- **Rate limit en test** : désactivé via `RATE_LIMIT_ENABLED=false` (app singleton partagé) ;
  réactivé dans un test dédié.
- **Event loop dans un test sync** : ne pas utiliser `asyncio.get_event_loop()` (loop stale
  en suite complète) → créer une `new_event_loop()`.

## 7. Conventions
- Code typé, commenté là où c'est utile (le « pourquoi », pas le « quoi »). Pas de sur-ingénierie.
- **Human-in-the-loop** sur toute action sortante (commande, message client, publication).
  Statut `draft`/`pending_*` → action humaine → `confirmed`/`published` + **audit** (`audit_log`).
- **Explicabilité** : toute suggestion/promo/prévision porte un champ `explanation`/`reason`.
- Migrations : une par changement de schéma, nommées `000N_slug.py`, réversibles.
- Tests : miroir de `app/`, défaut sqlite + mocks ; intégration pg derrière le marqueur.

## 8. Workflow git
- Brancher depuis `main`, commits atomiques, PR. Ne pas merger sans validation (sauf demande).
- Garder le gate vert ; valider les migrations sur un vrai pg+pgvector avant PR.

## 9. Où regarder
- API : `backend/app/api/v1/` (`router.py` agrège). Endpoints : `docs/api-design.md`.
- Démo : `docs/DEMO.md`. Déploiement : `docs/DEPLOY.md`. Tenancy/rôles : `docs/multitenancy.md`.
- Dossier delivery (discovery/strategy/archi C4/ADRs) : `docs/delivery/`.
