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
  alert, markdown_suggestion, recipe, recipe_item, production_plan, daily_briefing,
  briefing_item, tenant_connector**). **Exceptions voulues** (référentiels **globaux**, non tenant, non
  filtrés par le garde-fou) : `expense_category`, `signal_definition`, `signal_observation`
  (signaux externes = données publiques alignées aux ventes par date), **`platform_admin`,
  `subscription`, `organization`** (plan plateforme = l'**inverse** du garde-fou : le
  backoffice MyHanout gère *tous* les commerces — cf. §9 « Backoffice plateforme »).
- **Backoffice plateforme (cross-tenant)** : `get_platform_admin` pose `current_org=None`
  (garde-fou désactivé, accès à tous les commerces). Réservé aux `PlatformAdmin` **vérifiés
  en base** (pas seulement via claim JWT) et **audité** (`platform_service.platform_audit`).
  Un commerce `organization.status ∈ {suspended, cancelled}` bloque ses utilisateurs
  (`core/deps._ensure_org_active`).
- **Limite (garde-fou applicatif)** : le SQL brut (hors ORM) n'est PAS filtré par l'event
  → filtrer l'org explicitement **— idem pour un `DELETE`/`UPDATE` ORM en masse** (l'event
  ne couvre que les SELECT) : filtrer `organization_id` à la main (cf. remplacement des recos
  dans `recommendation_service`, `PgVectorStore`). Test d'isolation : `tests/test_tenancy.py`.
- **Defense-in-depth : RLS Postgres (Lot 4)** — en prod pg, la **Row-Level Security**
  (`FORCE`, migration `0025`) rattrape ce trou : même une requête SQL brute est filtrée
  par la policy `tenant_isolation` (`organization_id = current_setting('app.current_org')`).
  Le GUC est posé par `core/rls.py::set_session_org` à l'auth (org réelle) et réinitialisé
  par requête (`get_session`) ; vide/NULL = accès complet (plateforme/seed/workers).
  No-op sur sqlite (tests). Ne dispense PAS de filtrer le SQL brut à la main (RLS = 2ᵉ filet).

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
  **Connecteurs par commerce (self-service, modèle B)** : `tenant_connector` (secrets
  **chiffrés** via `core/crypto.py`, clé dérivée de `SECRET_KEY` → **à changer en prod**),
  `services/connector_service.py` (split public/secret, `get_credentials`/`status`),
  résolveurs tenant-aware `messaging/resolver.py` (config du tenant → sinon `.env` → mock),
  API owner-only `api/v1/connectors.py` (`/connectors/manage`), composant front
  `ConnectorSettings.tsx`. Le briefing envoie via le résolveur (numéro du commerce).
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
- **Système multi-agents** : blueprint `docs/multi-agent-system.md` (équipe d'agents
  spécialisés + orchestration human-in-command, adapté proximité alimentaire). Agents :
  `intelligence/agents/` (registre `AGENT_CLASSES`, orchestrateur `intelligence/llm/orchestrator.py`).
- **Démarque (anti-gaspi frais)** : agent Démarque — moteur de règles pur
  `intelligence/markdown/engine.py` (perte évitée vs cash récupéré selon DLC & écoulement),
  `services/markdown_service.py`, `api/v1/markdown.py` (`/markdown`, `/scan`,
  `/{id}/apply|reject`), modèle `markdown_suggestion`, page front `Markdown.tsx`
  (module `markdown`). Réglages : `markdown_*` dans `config.py`.
- **Production & recettes** : agent Production — nomenclature (`recipe`/`recipe_item`),
  moteur pur `intelligence/production/engine.py` (besoin net arrondi au rendement),
  `services/recipe_service.py` (CRUD) + `services/production_service.py` (plan + besoins
  ingrédients agrégés), `api/v1/recipes.py` & `api/v1/production.py` (`/recipes`,
  `/production/plan`, `/scan`, `/{id}/confirm|dismiss`), modèle `production_plan`,
  page front `Production.tsx` (module `production`).
- **Briefing du matin** (orchestration proactive) : agent « Tâches du jour »
  (`agent_briefing`) + `services/briefing_service.py` qui **consolide** alertes +
  réassort + démarque + production en tâches priorisées (modèles `daily_briefing`/
  `briefing_item`). `api/v1/briefing.py` (`/briefing`, `/generate`, `/{id}/send`,
  `/items/{id}/done`). Câblé dans le **cycle quotidien** (`pipeline_service` job
  `daily` → asset `_asset_briefing`). Envoi WhatsApp/Slack (mock). Page `Briefing.tsx`
  (module `briefing`). Blueprint complet : `docs/multi-agent-system.md`.
- **Bilan hebdomadaire** (agent Bilan) : `services/report_service.py` consolide la semaine
  (CA vs S-1, marge via `finance/margin_service`, top ventes, alertes, démarque récupérée,
  réassort) en points clés + 3 actions. `api/v1/report.py` (`/report/weekly`, `/weekly/send`
  WhatsApp via résolveur). Agent `agent_report`, page `Report.tsx` (module `report`).
- **Contrôles & pertes** : `services/control_service.py` — 3-way match factures
  (facturé vs dernier coût connu vs commande fournisseur, tolérance `control_price_tolerance_pct`)
  + démarque inconnue (snapshot de référence + achats − ventes vs stock réel, valorisée
  au coût, seuil `shrinkage_min_units`). `api/v1/controls.py` (`/controls/invoices`,
  `/controls/shrinkage`), page `Controls.tsx` (module `controls`). Aucune table dédiée.
- **Hygiène (HACCP)** : carnet sanitaire — plan de nettoyage tracé (`hygiene_task`/
  `hygiene_record`, plan par défaut bootstrappé au 1er accès) + conformité chaîne du
  froid (dérivée de `temperature_reading`) + **registre** consolidé prêt pour contrôle.
  `services/haccp_service.py`, `api/v1/haccp.py` (`/haccp/tasks`, `/tasks/{id}/complete`,
  `/haccp/register`), page `Haccp.tsx` (module `haccp`), migration `0021_haccp`.
- **Prix & Effectifs** (agents conseil) : moteurs purs `intelligence/pricing/engine.py`
  (marge cible + arrondi psychologique, jamais sous le coût) et
  `intelligence/staffing/engine.py` (affluence prévue par jour de semaine → renfort).
  `services/pricing_service.py` (+ `apply_price` → `price_history`),
  `services/staffing_service.py`. `api/v1/pricing.py` (`/pricing/suggestions|apply`),
  `api/v1/staffing.py` (`/staffing/plan`). Pages `Pricing.tsx`/`Staffing.tsx`
  (modules `pricing`/`staffing`). Réglages : `pricing_*`/`staffing_*` dans `config.py`.
- **Backoffice plateforme (SaaS, agent-as-a-service)** : plan **cross-tenant** pour
  l'opérateur MyHanout — l'**inverse** du garde-fou (cf. §5). Modèles **globaux** (non
  tenant) `platform_admin` (rôles `superadmin`/`support`/`billing`) + `subscription`
  (plan/MRR) + `organization.status` (cycle de vie : `active`/`trial`/`suspended`/
  `cancelled`). Auth vérifiée **en base** `core/platform_auth.py` (`get_platform_admin`,
  `require_platform_scope`) → pose `current_org=None`. Service `services/platform_service.py`
  (vue 360 clients, `overview`, `provision_client`, `set_org_status`, `set_plan`) — **toute
  mutation auditée** (`platform_audit`, préfixe `platform.`). API owner-only
  `api/v1/platform.py` (`/platform/overview|clients|clients/{id}` + `/status` + `/plan`).
  Suspension d'un commerce → blocage immédiat de ses users (`deps._ensure_org_active`).
  Le login expose `platform_role` (claim `plat`, indice UX ; l'accès reste vérifié en base).
  Seed : opérateur `platform@myhanout.example`. Migration `0023`. Tests `tests/test_platform.py`.
- **Support & mises à jour (Lot 3)** : tickets **tenant** (`support_ticket`/`support_message`,
  `TenantMixin`) — le commerçant ne voit que les siens (garde-fou), l'opérateur les voit
  **tous** (`current_org=None`, audité). Changelog produit **global** (`release_note`, non
  tenant ; publié → visible par tous les commerces). `services/support_service.py`
  (⚠️ écriture cross-tenant : la réponse plateforme estampille `organization_id`
  **explicitement** ; recharge colonnes+messages via requêtes pour éviter le lazy-load async).
  API commerçant `api/v1/support.py` (`/support/tickets`, `/releases`) + section opérateur
  dans `api/v1/platform.py` (`/platform/tickets`, `/tickets/{id}/reply|status`, `/releases`).
  Front : page `Support.tsx` (commerçant) + tickets/notes dans `Admin.tsx`. Module `support`
  (socle CORE). Migration `0024`. Tests `tests/test_support.py`.
- **Livraison continue & MLOps (Lot 5)** : CD `.github/workflows/cd.yml` (build+push images
  GHCR sur `main`→`:main`/`:sha`, tag `v*`→`:version`/`:latest`). **Registre de modèles**
  `model_artifact` (TenantMixin, migration `0026`, RLS incluse) : 1 version **active** par
  (produit, modèle) + métriques + déclencheur (`manual`/`scheduled`/`drift`/`seed`).
  `services/model_registry_service.py` (`retrain_product`/`retrain_all`/`retrain_on_drift`,
  ⚠️ désactivation = mutation d'instances chargées, pas d'`UPDATE` en masse). Boucle dérive :
  `scan_alerts` émet `forecast_drift` (MAPE > `mlops_drift_mape_threshold`) → `retrain_on_drift`.
  Job pipeline `retrain` (planifié). API `/mlops/models|/retrain` (versionne). Front : registre
  dans `DataOps.tsx`. Artefacts sérialisés via `ArtifactStore` (ABC + mock keyless par défaut,
  MinIO en option — `intelligence/mlops/storage.py`) ; `artifact_uri` renseigné à chaque
  enregistrement. Tests `tests/test_model_registry.py`.
- **Idempotence webhooks entrants** : WhatsApp/Slack re-livrent parfois le même event
  (retries). Dédup par `external_id`/`event_id` dans la table **globale** `webhook_inbound`
  (`messaging/idempotency.py::mark_seen`, migration `0027`). Câblé dans `api/v1/whatsapp.py`
  (id du message) et `api/v1/slack.py` (`event_id`). Tests `tests/test_webhook_idempotency.py`.
- **Alerting (infra)** : Prometheus scrape `/metrics` (`docker-compose.data.yml` +
  `analytics/prometheus/`), datasource + **règles Grafana provisionnées**
  (`analytics/grafana/provisioning/alerting/rules.yml`). Le *contact point* de notification
  (Slack/email) reste à brancher par client.
