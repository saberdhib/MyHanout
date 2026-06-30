# 🏪 MyHanout AI — l'IA qui vous facilite la gestion de votre commerce

> Copilot IA pour les commerces de proximité (boucherie, épicerie, boulangerie, primeur…),
> piloté depuis **WhatsApp / Telegram / Slack** + un dashboard léger.
> Principe directeur : **human-in-the-loop · explicable · auditable · RGPD · multi-commerces.**

<p>
  <img alt="CI" src="https://github.com/saberdhib/MyHanout/actions/workflows/ci.yml/badge.svg" />
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-12B76A.svg" />
  <img alt="Python 3.11" src="https://img.shields.io/badge/python-3.11-blue.svg" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-async-009688.svg" />
  <img alt="React + Vite" src="https://img.shields.io/badge/React-Vite%20%2B%20TS-61DAFB.svg" />
  <img alt="status" src="https://img.shields.io/badge/statut-démo%20fonctionnelle-success.svg" />
</p>

MyHanout AI **prévoit la demande client et l'approvisionnement**, **comprend les dépendances
entre produits** (compléments / substituts), propose des **commandes de réassort explicables**,
**alerte** sur les ruptures, et vous laisse **communiquer & piloter votre commerce depuis votre
téléphone** (WhatsApp / Telegram / Slack). Il ingère aussi le passif documentaire (factures
PDF/photo via OCR) pour nourrir le tout — toujours sous contrôle humain.

<p align="center">
  <img src="website/public/shots/dashboard.png" alt="Dashboard MyHanout AI" width="49%" />
  <img src="website/public/shots/finance.png" alt="Couche financière (pré-compta)" width="49%" />
</p>
<p align="center">
  <img src="website/public/shots/recommendations.png" alt="Recommandations de réassort explicables" width="49%" />
  <img src="website/public/shots/data-ops.png" alt="Data Ops — orchestration des pipelines" width="49%" />
</p>
<p align="center">
  <img src="website/public/shots/promos.png" alt="Promo & communication client + affiche générée" width="49%" />
  <img src="website/public/shots/invoices.png" alt="Factures (OCR + import email)" width="49%" />
</p>

## ⚡ Démo en 1 minute (sans aucune clé API)

```bash
cp .env.example .env          # placeholders uniquement — aucune vraie clé requise
docker compose up -d --build  # postgres+pgvector, redis, api, worker, frontend
make seed                     # org démo + produits + 1 périssable en fin de vie + clients opt-in
# Dashboard : http://localhost:5173   ·   API : http://localhost:8000/docs   ·   login démo : admin / admin
```

Tout tourne **en mode mock par défaut** : OCR, LLM, images, WhatsApp, capteurs, caisse sont
simulés tant qu'aucune clé n'est fournie. Scénario pas-à-pas : **[`docs/DEMO.md`](docs/DEMO.md)**.

## 🎯 Ce que ce repo démontre

- **Architecture multi-tenant sécurisée** : garde-fou central (isolation par commerce), RBAC, audit — testé (A ≠ B).
- **Mock-first / keyless** : abstractions `Provider` partout → la démo tourne sans secret ; le réel s'active par `.env`.
- **Human-in-the-loop & explicabilité** : aucune action sortante sans validation ; chaque chiffre/suggestion porte sa raison.
- **MLOps pragmatique** : prévision → écart réel → MAE/MAPE → réentraînement versionné.
- **RGPD & socle générique** : consentement opt-in, données fictives, modules activables par type de commerce.

---

## ✨ Fonctions

| Domaine | Détail |
|---------|--------|
| 📥 Ingestion factures | OCR (Mistral + fallback PDF), drag & drop / photo WhatsApp/Telegram, **import email (IMAP)**, validation humaine, suivi **payé/non payé**, édition pré-remplie |
| 📊 Forecasting | Prévision de demande (naïf par défaut, Prophet/LightGBM en option) + saisonnalité/fêtes + **signaux externes** (météo, vacances scolaires, carburant, foot…) et **effets entre produits** (substituts/compléments) — voir ci-dessous |
| 🛒 Réassort | Suggestions **explicables** (demande + stock + délai + signaux), 3 modes d'envoi fournisseur |
| 🗂️ Catalogue | **Gestion produits** (créer/éditer) + **rangement par famille** (rayon), recherche/filtre |
| 📣 Communication & promos | Messages/offres rédigés par l'IA → **affiche générée (text-to-image)** → publication validée **WhatsApp/Telegram/Slack + réseaux + clients opt-in (RGPD)** |
| 💶 Gestion financière | **OPEX/CAPEX** (tagging IA explicable, validé humain), **trésorerie** (alerte cash), **valorisation stock**, **marges réelles** + alertes (doublon, prix, marge, échéance) — pré-compta |
| 🌡️ Chaîne du froid | Suivi **température** des machines (HACCP) via capteurs (mock keyless ou thermomètres connectés), **alertes explicables** anti-gaspillage |
| 🔌 Intégrations | **Import JSON** + **sync DWH** + **connecteur caisse (POS)** (ingestion ventes idempotente) + page **Connecteurs** (statut messagerie/data/IoT, sans secret) |
| 🛰️ Data platform | **Orchestration** de pipelines tracés (`PipelineRun`), **service ML isolé** (fallback in-process), **recos explicites** (substituts/signaux métier), **alertes** & **temps réel SSE**, page **Data Ops** — voir ci-dessous |
| 📱 Omni-accès | Web responsive + **PWA installable** (PC / téléphone / tablette de caisse) + WhatsApp/Telegram/Slack |
| 💬 Conversationnel | **WhatsApp, Telegram & Slack** (texte + photo→OCR) + **fenêtre de chat web flottante** (depuis n'importe quelle page), même cerveau d'agents |
| 🤖 Agents IA | order, stock, finance, marketing, support, governance + **mémoire** + **éval routage** |
| 🧠 RAG | Q&A citée sur ses propres factures (pgvector) |
| 🌤️ Compagnon | Signaux **météo + tendances** intégrés aux recommandations |
| 📈 MLOps | Écart prévu/réel → MAE/MAPE → réentraînement **versionné** |
| 🛡️ Gouvernance | Multi-tenant isolé, RBAC (owner/staff/accountant/read_only), audit, RGPD |

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Canaux
        WA[WhatsApp]
        TG[Telegram]
        WEB[Dashboard React]
    end
    subgraph App["Couche applicative — FastAPI"]
        API[API v1 + Auth JWT + tenant guard]
        MSG[Messaging + Publish]
    end
    subgraph Intel["Intelligence"]
        FC[Forecasting] 
        AG[Agents + Orchestrateur]
        LLM[LLM: Claude/Mistral/HF/mock]
        RAG[RAG pgvector]
        SIG[Signaux météo/tendances]
    end
    subgraph Data
        REPO[Repositories]
        MODELS[Modèles SQLAlchemy + TenantMixin]
    end
    subgraph Ingestion
        OCR[OCR mistral/pdf/mock] --> PARSE[Parsing] --> VALID[Validation]
    end
    WA & TG & WEB --> API
    API --> AG --> LLM
    AG --> FC & RAG
    API --> REPO --> MODELS --> PG[(PostgreSQL 16 + pgvector)]
    VALID --> REPO
    MSG --> WA & TG
    AG -.queue.-> WORKER[Celery + Redis]
```

Détails : [`docs/delivery/03-solution-architecture.md`](docs/delivery/03-solution-architecture.md)
(C4 + séquences), [`docs/architecture.md`](docs/architecture.md),
[`docs/data-model.md`](docs/data-model.md), [`docs/multitenancy.md`](docs/multitenancy.md).

---

## 📊 Forecasting — au-delà du MAE/MAPE

L'objectif n'est pas juste « prédire une courbe », mais **comprendre ce qui fait vendre**
et le mesurer honnêtement. Trois briques, toutes branchables et explicables :

**1. Signaux externes historiques (mets un maximum de data, vois ce qui pèse).**
Chaque source de données est un *provider* derrière une ABC (mock keyless par défaut,
HTTP réel via `.env`) et une **série déclarée** en base — donc on en ajoute autant qu'on veut :

| Série (clé) | Type | Hypothèse métier |
|-------------|------|------------------|
| `weather_temp_c`, `weather_rain` | météo | chaleur → boissons/glaces ; pluie → moins de passage |
| `school_holiday` | vacances scolaires | familles présentes → paniers différents |
| `public_holiday` | jours fériés | pics / fermetures |
| `fuel_price_eur_l` | prix carburant | pouvoir d'achat, mobilité |
| `football_match` | matchs de foot | snacks/boissons les soirs de match |

→ **Où mettre une nouvelle source / API** : déclarer une `SignalDefinition` (clé, libellé,
type, provider/source) + une impl de `ExternalSignalProvider` ; l'ingestion et la
corrélation sont génériques. Tables : `signal_definition` (registre) et `signal_observation`
(valeur par date + région). `POST /signals/ingest` tire l'historique (idempotent).

**2. Évaluer corrélation / coïncidence — et NE PAS confondre avec la causalité.**
`GET /forecasts/{id}/factors` aligne les ventes journalières du produit avec chaque signal,
calcule un **coefficient de Pearson**, classe les facteurs par force et rend un **verdict
honnête** (forte / modérée / faible, ou *données insuffisantes* sous 14 points) — avec
l'avertissement explicite **« corrélation ≠ causalité : à confirmer par un test (A/B, hold-out) avant d'agir »**.

**3. Effets entre produits (substituts / compléments).**
`GET /forecasts/{id}/cross-product` corrèle les co-ventes journalières : corrélation **positive
→ complément** (se vendent ensemble), **négative → substitut** (l'un monte quand l'autre manque
en rayon). De quoi anticiper le report de demande en cas de rupture.

> Tout est **tenant-scopé** côté ventes (garde-fou central) ; les signaux sont des **données
> publiques globales** (comme `expense_category`). Boucle MLOps inchangée : prévision → écart
> réel → MAE/MAPE → réentraînement versionné, désormais **nourrie par les facteurs retenus**.

Détails : [`docs/ai-models.md`](docs/ai-models.md), [`docs/api-design.md`](docs/api-design.md).

---

## 🛰️ Socle data platform (orchestration → décision → temps réel)

Au-delà des fonctions métier, MyHanout pose un socle « supply-chain frais » sérieux,
**intégré** à l'archi (multi-tenant, mock-first, human-in-the-loop, explicable) :

- **Orchestration tracée** — chaque traitement (snapshot stock, ingestion signaux,
  recommandations, alertes) tourne sous un `PipelineRun` (statut, lignes, fraîcheur,
  erreur). Toute donnée produite référence le **run** qui l'a générée. Choix assumé :
  **Celery + `PipelineRun`** (pas de Dagster) — zéro infra neuve, testable in-process.
  Endpoints `/pipelines/*`, page **Data Ops** (santé, fraîcheur, déclenchement manuel).
- **Service ML isolé** — le forecast peut tourner dans un service dédié (`ml-service/`,
  scalable à part) derrière `ForecastServiceClient` (`inprocess` | `http`) avec
  **fallback in-process** si le service est down. `model_version` partout (MLOps).
- **Recommandations explicites** — règles lisibles/auditables (rupture, surstock,
  saisonnalité, **signal métier du commerçant** : match/paie/braderie, périssable,
  fallback) ; chaque reco porte quantité, confiance, risque, score, **explication** et
  données utilisées. **Simulation** « et si je commande X ? ».
- **Alertes & temps réel** — alertes décisionnelles (règle → priorité → **résolution
  humaine** auditée) et flux **SSE** `/stream/events` **filtré par tenant** (un commerce
  ne reçoit jamais les events d'un autre) ; le dashboard se met à jour sans refresh.
- **Observabilité** — `/health` étendu (db/redis/ml-service), métriques Prometheus des runs.
- **Tests E2E** — Playwright sur les parcours critiques (`e2e/`), stack keyless bootée.

Détails : [`docs/data-engineering.md`](docs/data-engineering.md), [`ml-service/README.md`](ml-service/README.md).

## 🚀 Quickstart (démo, 100 % mock, sans aucune clé)

```bash
cp .env.example .env
docker compose up -d --build          # postgres+pgvector, redis, api, worker, frontend
make seed                             # org démo + produits + 1 périssable en fin de vie + clients opt-in
```
| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API / Swagger | http://localhost:8000/docs |
| Health / Metrics | http://localhost:8000/health · /metrics |

Login démo (auto en dev) : `admin@myhanout.example` / `admin`.
👉 **Script de démo guidé** : [`docs/DEMO.md`](docs/DEMO.md).

### Activer le réel (tes clés dans `.env`)
HuggingFace, Claude, Mistral, WhatsApp Business, Telegram — chaque provider est optionnel
et **retombe sur le mock sans clé**. Table d'activation + déploiement prod :
[`docs/DEPLOY.md`](docs/DEPLOY.md).

```bash
# Production (frontend buildé + nginx, migrations auto)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 🔌 API (extrait)

`/auth/*` · `/onboarding/*` (signup, invitations) · `/stocks` · `/invoices` (upload,
approve, reject, **PATCH** édition + payé, **import/email**) · `/forecasts/{id}` ·
`/forecasts/{id}/factors` · `/forecasts/{id}/cross-product` ·
`/orders` (suggest, confirm 3 modes) · `/daily-entries` · `/mlops/*` ·
`/promos` (scan, **visual**, publish) · `/import` (json, dwh/sync) ·
`/finance` (treasury, inventory-value, margins, categories, expenses, classify, alerts) · `/customers` ·
`/signals` (definitions, observations, **ingest**) · `/pipelines/*` (runs, trigger, health) ·
`/recommendations` (+ simulate) · `/alerts` (+ resolve) · `/stream/events` (SSE) ·
`/chat` · `/rag/*` · `/agents/eval` · `/whatsapp/webhook` ·
`/telegram/webhook` · `/slack/webhook` · `/api-keys` · `/webhooks` · `/config/connectors`.
Détail : [`docs/api-design.md`](docs/api-design.md).

> **Ouvert & interopérable** : API REST + **clés API** (`X-API-Key`) + **webhooks sortants**
> signés HMAC → branchez **n8n / Make / Zapier** (un MCP pour agents IA est au programme).

---

## 🛡️ Sécurité, RGPD & pricing
- **Isolation multi-commerces** par garde-fou central (un commerce ne voit jamais un autre).
- **RBAC** : owner / staff / accountant (multi-commerces) / read_only.
- **RGPD** : consentement explicite, minimisation, audit, mock-first (rien ne sort sans config).
- **Human-in-the-loop** : aucune action sortante sans validation ; tout est audité.
- **Pricing humain** : pas de coupure brutale (grâce, rétrogradation). Cf.
  [`docs/delivery/privacy-pricing.md`](docs/delivery/privacy-pricing.md).
- **Aucun secret en repo** : tout via `.env` (non suivi) ; `.env.example` = placeholders.
  Signaler une faille : [`SECURITY.md`](SECURITY.md).

---

## 🧰 Développement & qualité
```bash
make check        # ruff + mypy + pytest
pre-commit install
```
Stack : Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · Alembic ·
Celery/Redis · PostgreSQL 16 + pgvector · React/Vite/TS/Tailwind.
Tests : sqlite (rapide) + intégration **pg+pgvector** (job CI). Migrations réversibles.
**Contribuer ? Lis [`CLAUDE.md`](CLAUDE.md)** (architecture, conventions, pièges).

---

## 📁 Structure
```
backend/    FastAPI, modèles (TenantMixin), ingestion, intelligence, messaging, workers, alembic
frontend/   Dashboard (app authentifiée) React + Vite + TS + Tailwind (dark mode) — chat, promos, factures…
website/    Site vitrine public Astro + Tailwind (SSG, SEO) — landing, tarifs, confiance/RGPD, contact
analytics/  Couche analytique : dbt (staging→marts) + Airflow (DAG ELT) + Grafana
data/seeds/ Données factices (démo)
docs/       architecture, data-model, api-design, multitenancy, configuration, data-engineering, ai-models, DEMO, DEPLOY
```
> **Cœur (fixe) vs mouvant (par client)** : ce qui est versionné = le produit ;
> ce qui change pour brancher un commerce (`.env`, données tenant, seed) est isolé.
> Carte complète : [`docs/configuration.md`](docs/configuration.md).
> Données : [`docs/data-engineering.md`](docs/data-engineering.md) · Modèles IA & MLOps : [`docs/ai-models.md`](docs/ai-models.md).
> Socle retail générique (audit + modules par vertical) : [`docs/retail-platform.md`](docs/retail-platform.md) · Roadmap : [`docs/roadmap.md`](docs/roadmap.md).
> `frontend/` = l'**app** (le commerçant connecté). `website/` = la **vitrine** publique
> (prospects, SEO). Deux fronts distincts dans le même monorepo. Cf. [`website/README.md`](website/README.md).

## 🗺️ Roadmap
Faits : OCR réel, factures (review + payé + **import email**), auth JWT/RBAC, multi-tenant,
WhatsApp+Telegram, boucle quotidienne, suggestions, promos RGPD + **affiches générées**,
**import JSON / sync DWH**, **couche financière (OPEX/CAPEX, trésorerie, marges, alertes)**,
RAG, MLOps, rate limiting, tracing, dark mode.
Prochaines briques : Prophet/LGBM en prod, connecteurs réseaux réels,
voice WhatsApp, billing enforcement. Détail : [`docs/roadmap.md`](docs/roadmap.md).

---

## 📜 Licence

[MIT](LICENSE) — librement réutilisable. Sécurité : [`SECURITY.md`](SECURITY.md).
