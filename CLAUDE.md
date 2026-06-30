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
- **Frontend (app)** : `frontend/` — dashboard authentifié, React + Vite + TypeScript + Tailwind (dark mode).
- **Vitrine (site public)** : `website/` — Astro + Tailwind, statique (SSG, SEO). Marketing/landing,
  séparé de l'app. Réutilise les mêmes tokens de marque. `cd website && npm run build`. CTA → `PUBLIC_APP_URL`.
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
- `ImageProvider` (mock | huggingface) — `intelligence/imaging/` : génère les **affiches promo** (text-to-image). Le mock rend une affiche **SVG déterministe** (data URL), zéro réseau.
- `MailboxProvider` (mock | imap) — `ingestion/email/` : récupère les factures **par email** (pièces jointes → pipeline OCR existant, idempotent par hash).
- `DwhSyncTarget` (mock | http) — `ingestion/dwh.py` : pousse un snapshot (catalogue/stock/ventes) vers un **entrepôt de données**.
- `ExpenseClassifier` (mock | llm) — `intelligence/finance/` : tagging OPEX/CAPEX des factures.
- `SensorProvider` (mock | http) — `ingestion/sensors/` : relevés de **température** (chaîne du froid). Mock déterministe, zéro matériel.
- `POSConnector` (mock | http) — `ingestion/pos/` : ingestion des **ventes caisse** (idempotent par `external_ref`).
- `WhatsAppClient` (mock | business) — `messaging/whatsapp/`
- `TelegramClient` (mock | bot) — `messaging/telegram.py`
- `SlackClient` (mock | bot) — `messaging/slack.py` (+ webhook `api/v1/slack.py`, Events API)
- `PublishChannel` (social | customers) — `messaging/publish.py`
- `ForecastModel` (naive | prophet | lgbm) — `intelligence/forecasting/`
- `ExternalSignalProvider` (mock | http) — `ingestion/signals_ext/` : **signaux externes
  historiques** (météo, vacances scolaires, prix carburant, matchs de foot…) pour le
  forecasting. Mock = séries déterministes keyless. Point d'extension : déclarer une
  `SignalDefinition` + une impl ; ingestion/corrélation génériques.
- `SignalSource` (mock | …) — `ingestion/merchant_signals/` : **signaux métier du
  commerçant** (match local, jour de paie, braderie…), tenant (`external_signal`),
  croisés avec les séries publiques par le moteur de reco. Mock keyless.
- `ForecastServiceClient` (inprocess | http) — `intelligence/forecasting/service_client.py` :
  forecast in-process (défaut keyless) ou via le **service ML isolé** (`ml-service/`),
  avec **fallback in-process** si le service HTTP est down. `model_version` partout.

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
  daily_entry, forecast_evaluation, customer, promo_campaign, agent_memory, document_chunk,
  expense_classification_feedback, equipment, temperature_reading, price_history,
  meat_lot, meat_cut, **pipeline_run, inventory_snapshot, external_signal, recommendation,
  alert**). **Exceptions voulues** (référentiels **globaux**, non tenant, non
  filtrés par le garde-fou) : `expense_category`, `signal_definition`, `signal_observation`
  (signaux externes = données publiques alignées aux ventes par date).
- **Limite** : le SQL brut (hors ORM) n'est PAS filtré → filtrer l'org explicitement
  **— idem pour un `DELETE`/`UPDATE` ORM en masse** (l'event ne couvre que les SELECT) :
  filtrer `organization_id` à la main (cf. remplacement des recos dans `recommendation_service`).
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
- **État partagé entre tests** : la base sqlite mémoire est **partagée** sur toute la session
  (cache `mode=memory&cache=shared`). Un test qui insère (import email, scan promo…) pollue les
  listes vues par les autres → **ne pas présumer de l'ordre** d'une liste (`items[0]`). Chercher
  l'élément voulu (`any(...)`), ou créer ses données dans une org dédiée. (Bug : un import de
  factures `pending_review` sans lignes passait devant la facture seedée et cassait `items[0]`.)

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
- **Affiches promo** : `POST /promos/{id}/visual` (provider `intelligence/imaging/`).
- **Import factures email** : `POST /invoices/import/email` (provider `ingestion/email/`).
- **Import JSON / sync DWH** : `POST /import/json`, `POST /import/dwh/sync`
  (`services/import_service.py`, `ingestion/dwh.py`). Frontend : page « Intégrations ».
- **Couche financière** (pré-compta / pilotage) : endpoints `/finance/*`
  (`api/v1/finance.py`), services `services/finance/`, classifieur OPEX/CAPEX
  `intelligence/finance/` (ABC + mock keyless + llm), alertes `intelligence/finance/alerts.py`.
  Référentiel global `expense_category` (non tenant). Voir `docs/data-model.md`.
- **Site vitrine** : `website/` (Astro). Pages dans `website/src/pages/`, composants
  `website/src/components/`, tokens de marque dupliqués dans `website/tailwind.config.mjs`
  (garder synchro avec `frontend/src/theme/tokens.js`). Détails : `website/README.md`.
- **Cœur vs mouvant (par client)** : `docs/configuration.md` — ce qui est versionné
  (produit, fixe) vs ce qui change pour brancher un commerce (`.env`, données tenant,
  seed). **Ne jamais coder une valeur spécifique client dans `backend/app/`.**
- **Data engineering** : `docs/data-engineering.md` (ELT/ETL, pg, dbt, Airflow,
  Grafana, MinIO, contrats d'entrée). Stack : `docker-compose.data.yml`, `analytics/`.
- **Modèles IA & MLOps** : `docs/ai-models.md` (variables `.env` par capacité,
  réglage des paramètres, boucle MLOps).
- **Socle retail générique** : `docs/retail-platform.md` (audit + modules par
  vertical). Registry `app/core/modules.py` + `GET /config/modules` ; la nav
  frontend se filtre par module actif selon le `business_type` du commerce.
- **Boucherie** : `services/meat_service.py` (lot→coupes, rendement, coût/kg,
  traçabilité), `api/v1/meat.py`. **Catalogue/prix** : `api/v1/catalog.py`
  (gestion produits : `GET/POST /catalog/products`, `PATCH /catalog/products/{id}`,
  familles), `services/price_service.py`, `schemas/catalog.py`. Page front `Catalog.tsx`.
  Familles produit : `PRODUCT_FAMILIES` (base.py).
- **Conversationnel & connecteurs** : WhatsApp (`messaging/whatsapp/`), Telegram
  (`messaging/telegram.py`), **Slack** (`messaging/slack.py` + `api/v1/slack.py`),
  chat web (`api/v1/chat.py`) + **fenêtre de chat flottante** front (`components/ChatWidget.tsx`,
  montée dans `Layout`). État des connecteurs **sans secret** : `GET /config/connectors`
  (page front `Connectors.tsx`). Assets de marque à fournir : `docs/brand-assets.md`.
- **Ouverture / interopérabilité** : **clés API** (`X-API-Key`, table `api_key` hashée +
  préfixe, scopes RBAC ; `core/security.generate_api_key`, résolution dans `core/deps`,
  endpoints `api/v1/api_keys.py` owner-only) et **webhooks sortants** signés HMAC
  (`webhook_endpoint`, `services/webhook_service.py`, `api/v1/webhooks.py`) — déclenchés sur
  `alert_created` & `pipeline_finished` (n8n/Make/Zapier). Front : `components/ApiAccess.tsx`.
  ⚠️ `webhook_service.deliver` filtre l'org **explicitement** (pas seulement via le garde-fou).
- **Forecasting avancé** : signaux externes (`ingestion/signals_ext/` + tables globales
  `signal_definition`/`signal_observation`, `services/signals_service.py`,
  `api/v1/signals.py` : definitions/observations/ingest) et analyse
  (`intelligence/forecasting/correlation.py` : Pearson, verdict, cross-product).
  Endpoints `GET /forecasts/{id}/factors` et `/cross-product`. Corrélation ≠ causalité
  (verdict prudent). Doc : `docs/ai-models.md` §5.
- **Socle data platform** : orchestration (`services/pipeline_service.py` : jobs =
  suites d'assets sous un `PipelineRun` tracé, Celery, pas Dagster ; `api/v1/pipelines.py`),
  service ML isolé (`ml-service/` + `intelligence/forecasting/service_client.py`, fallback
  in-process), moteur de reco explicite (`intelligence/recommendation/engine.py` règles
  pures + `services/recommendation_service.py`), alertes (`services/alert_service.py`,
  `api/v1/alerts.py`), temps réel **SSE** filtré tenant (`core/events.py`, `api/v1/stream.py`).
  Schéma dev/E2E sqlite : `app/db/create_all.py`. E2E Playwright : `e2e/`. Doc :
  `docs/data-engineering.md`.
