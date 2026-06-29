# Cœur du projet vs configuration mouvante (par client)

> Règle de lecture du repo : **ce qui est versionné = le cœur produit (fixe, commun
> à tous les commerces)** ; **ce qui change pour se connecter à un client = la
> configuration mouvante (jamais committée en clair)**. Cette page dit précisément
> où est la frontière.

## 1. 🧱 Cœur du projet (FIXE — versionné, commun à tous les tenants)

C'est le produit. On ne le modifie pas pour brancher un commerce donné.

| Zone | Chemin | Rôle |
|------|--------|------|
| Backend (logique métier) | `backend/app/` | API, services, modèles, garde-fou multi-tenant |
| Abstractions providers | `backend/app/ingestion/`, `intelligence/`, `messaging/` | Interfaces ABC + impl **mock** par défaut |
| Schéma & migrations | `backend/alembic/versions/` | Évolution de la base (chaînée, réversible) |
| Tests | `backend/tests/` | Batterie (sqlite + intégration pg) |
| App (dashboard) | `frontend/` | UI authentifiée |
| Vitrine | `website/` | Site marketing public |
| Analytique | `analytics/dbt`, `analytics/airflow` | Modèles dbt + DAG (logique, pas les secrets) |
| CI/CD | `.github/workflows/` | Gate lint/type/tests/intégration/build |
| Docs | `docs/`, `CLAUDE.md`, `README.md` | Référence |

**Invariant** : le cœur tourne **sans aucune clé** (tout en mock). Si un changement
« pour un client » oblige à toucher le cœur, c'est qu'il manque un point d'extension
(provider/abstraction) — on l'ajoute proprement plutôt que de spécialiser le cœur.

## 2. 🔌 Mouvant par client (CONFIG — pour se connecter à LUI, hors-repo)

Ce qui diffère d'un commerce/déploiement à l'autre. **Jamais de secret committé.**

### a) Variables d'environnement (`.env`, gabarit `.env.example`)
On bascule un provider de `mock` → réel et on fournit ses identifiants :

| Catégorie | Variables | Effet |
|-----------|-----------|-------|
| Base/infra | `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` | cible de déploiement |
| IA | `LLM_PROVIDER`, `HUGGINGFACE_API_KEY`, `EMBEDDING_PROVIDER`, `IMAGE_PROVIDER`, `OCR_PROVIDER`, `FORECAST_MODEL` | quels modèles (cf. `docs/ai-models.md`) |
| Messagerie | `WHATSAPP_*`, `TELEGRAM_*` | canaux du commerce |
| Sources data | `POS_CONNECTOR`+`POS_URL`, `SENSOR_PROVIDER`+`SENSOR_HTTP_URL`, `EMAIL_IMAP_*`, `DWH_TARGET`+`DWH_URL` | caisse, capteurs, email, entrepôt |
| Analytique | `~/.dbt/profiles.yml`, identifiants MinIO/Grafana | connexion entrepôt/observabilité |

### b) Données propres au tenant (en base, pas en code)
Créées à l'onboarding / via l'app — **isolées par `organization_id`** :
- organisation, membres & rôles ;
- catalogue **produits + prix**, fournisseurs, stock ;
- **identifiants capteurs** (`equipment.sensor_external_id`), réf. caisse (`sale.external_ref`) ;
- clients opt-in (RGPD), campagnes, factures.

> Exception : `expense_category` est un **référentiel global** (commun), pas tenant.

### c) Données de démarrage (seed) — remplaçables par client
- `data/seeds/` (`products.csv`, `suppliers.csv`, `sales.csv`, `invoices.json`) :
  jeu de **démo**. Pour un vrai commerce, on alimente via import (JSON, email, caisse)
  plutôt que par ces fichiers.

## 3. Comment brancher un nouveau client (checklist)

1. Déployer le cœur (inchangé) — `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.
2. Créer son `.env` (clés IA, canaux, sources) à partir de `.env.example`.
3. Onboarding : créer l'organisation + premier owner (self-service).
4. Alimenter ses données : import catalogue/ventes (JSON), email factures, caisse (POS),
   capteurs (ids). Tout est **idempotent**.
5. Optionnel : brancher l'analytique (dbt profiles → entrepôt, dashboards Grafana).

## 4. Convention pour les contributeurs

- **Ne jamais** coder une valeur spécifique à un commerce dans `backend/app/` :
  passer par `.env` (config) ou la base (données tenant).
- **Ajouter une intégration** = nouvelle impl derrière l'ABC + fabrique + fallback
  mock + test (cf. `CLAUDE.md` §4). Le cœur reste générique.
- Tout secret → `.env` / gestionnaire de secrets, jamais le repo.

Voir aussi : [`docs/ai-models.md`](ai-models.md), [`docs/data-engineering.md`](data-engineering.md),
[`docs/DEPLOY.md`](DEPLOY.md), [`docs/multitenancy.md`](multitenancy.md).
