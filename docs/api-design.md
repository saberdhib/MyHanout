# API Design — MyHanout AI

API REST FastAPI, versionnée sous `/api/v1`. Doc interactive : `/docs` (Swagger).

## Conventions

- **Versioning** par préfixe d'URL (`/api/v1`).
- **Réponses listes** : `{ "items": [...], "total": n }` (`ListResponse[T]`).
- **Erreurs** : `{ "error": { "code": "...", "message": "..." } }` (cf. `core/exceptions.py`).
- **Auth/RBAC** : JWT Bearer. `POST /auth/login` renvoie access + refresh tokens ;
  `get_current_user` résout l'utilisateur depuis le token ; `require_permission(scope)`
  applique le RBAC (scopes du rôle, `*` = tous). Sans token → 401, scope manquant → 403.
- **Audit** : middleware trace toutes les requêtes mutantes ; actions sensibles
  persistées dans `audit_log`.

## Endpoints (MVP)

| Méthode | Chemin                         | Description                                   | Scope     |
|---------|--------------------------------|-----------------------------------------------|-----------|
| GET     | `/health`                      | Healthcheck                                   | —         |
| GET     | `/metrics`                     | Métriques Prometheus                          | —         |
| POST    | `/api/v1/auth/login`          | Login → access + refresh tokens               | —         |
| POST    | `/api/v1/auth/refresh`        | Échange refresh token → nouvel access token   | —         |
| GET     | `/api/v1/auth/me`              | Utilisateur courant (+ org active)            | (token)   |
| POST    | `/api/v1/onboarding/signup`   | Crée compte + organisation (owner)            | —         |
| POST    | `/api/v1/onboarding/products` | Ajoute un produit (rattaché à l'org)          | stocks    |
| POST    | `/api/v1/onboarding/suppliers`| Ajoute un fournisseur (rattaché à l'org)      | stocks    |
| POST    | `/api/v1/onboarding/invitations`| Invite un membre (owner choisit le rôle)    | owner     |
| POST    | `/api/v1/onboarding/invitations/accept`| Accepte une invitation               | —         |
| POST    | `/api/v1/invoices/upload`     | Importe un document → facture `pending_review`| invoices  |
| POST    | `/api/v1/invoices/{id}/approve`| Validation humaine → écrit les lignes + audit | invoices  |
| POST    | `/api/v1/invoices/{id}/reject`| Rejet humain avec motif (audité)              | invoices  |
| PATCH   | `/api/v1/invoices/{id}`       | Édite (n°/date/fournisseur/montant) + payé    | invoices  |
| POST    | `/api/v1/invoices/import/email`| Import factures depuis la boîte mail (IMAP/mock)| invoices |
| POST    | `/api/v1/promos/scan`         | Détecte fins de vie → promos (brouillons)     | marketing |
| POST    | `/api/v1/promos/{id}/visual`  | Génère l'affiche promo (text-to-image)        | marketing |
| POST    | `/api/v1/promos/{id}/publish` | Publie (réseaux + clients opt-in RGPD)        | marketing |
| POST    | `/api/v1/import/json`         | Import catalogue/ventes JSON (idempotent SKU) | stocks    |
| POST    | `/api/v1/import/dwh/sync`     | Pousse un snapshot vers l'entrepôt de données | stocks    |
| GET     | `/api/v1/finance/treasury`    | Vue trésorerie (entrées/sorties + alerte cash)| finance   |
| GET     | `/api/v1/finance/inventory-value`| Valeur du stock (dont périssable à risque) | finance   |
| GET     | `/api/v1/finance/margins`     | Marge par produit + signal de dégradation     | finance   |
| GET     | `/api/v1/finance/categories`  | Référentiel catégories de charges (OPEX/CAPEX)| finance   |
| GET     | `/api/v1/finance/expenses`    | Factures + classification (à valider/corriger)| finance   |
| POST    | `/api/v1/finance/expenses/classify-all`| Suggestion IA sur factures non classées| finance |
| POST    | `/api/v1/finance/invoices/{id}/classify`| Suggestion IA (catégorie/kind/explication)| finance |
| POST    | `/api/v1/finance/invoices/{id}/classification`| Validation/correction humaine (tracée)| finance |
| GET     | `/api/v1/finance/alerts`      | Alertes finance (doublon, prix, marge, échéance)| finance |
| GET     | `/api/v1/equipment`           | Statut chaîne du froid (dernier relevé + plage) | stocks    |
| POST    | `/api/v1/equipment`           | Déclare un équipement à suivre (capteur opt.)   | stocks    |
| POST    | `/api/v1/equipment/poll`      | Relève les capteurs (mock keyless ou réel)      | stocks    |
| POST    | `/api/v1/import/pos/sync`     | Ingestion ventes caisse (POS), idempotent       | stocks    |
| GET     | `/api/v1/config/modules`      | Modules actifs selon le type de commerce        | (auth)    |
| GET     | `/api/v1/catalog/families`    | Familles produit suggérées                      | stocks    |
| GET     | `/api/v1/catalog/products`    | Liste produits (filtre `?family=`/`?search=`)   | stocks    |
| POST    | `/api/v1/catalog/products`    | Crée un produit (SKU unique)                    | stocks    |
| PATCH   | `/api/v1/catalog/products/{id}`| Édite un produit (nom, famille, prix, péremption) | stocks  |
| GET/POST| `/api/v1/catalog/products/{id}/prices`| Historique des prix (lecture / ajout)   | stocks    |
| GET/POST| `/api/v1/meat/lots`           | Lots boucherie (liste / réception bête)         | stocks    |
| PUT     | `/api/v1/meat/lots/{id}/breakdown`| Décomposition (coupes prévu/réel)           | stocks    |
| GET     | `/api/v1/meat/lots/{id}`      | Rendement + coût/kg + traçabilité d'un lot      | stocks    |
| POST    | `/api/v1/orders/suggest`      | Suggestion de commande explicable (par ligne) | orders    |
| POST    | `/api/v1/orders/confirm`      | Valide une suggestion ajustée (3 modes)       | orders    |
| GET/POST| `/api/v1/daily-entries`       | Saisie de fin de journée (idempotent, audité) | stocks    |
| GET     | `/api/v1/mlops/metrics`       | MAE/MAPE par produit/modèle (écarts)          | forecasts |
| POST    | `/api/v1/mlops/retrain`       | Réentraîne le modèle + versionne              | forecasts |
| GET     | `/api/v1/agents/eval`         | Précision de routage des agents (golden set)  | forecasts |
| POST    | `/api/v1/rag/index/invoices/{id}`| Indexe une facture (RAG pgvector)          | invoices  |
| POST    | `/api/v1/rag/query`           | Q&A citée sur les documents (RAG, tenant)     | invoices  |
| GET     | `/api/v1/stocks`              | Liste des stocks (+ nom produit)              | stocks    |
| GET     | `/api/v1/stocks/alerts`       | Stocks sous le seuil de réassort              | stocks    |
| GET     | `/api/v1/invoices`            | Factures + lignes                             | invoices  |
| GET     | `/api/v1/forecasts/{id}`      | Prévision de demande d'un produit             | forecasts |
| GET     | `/api/v1/forecasts/{id}/factors` | Facteurs externes corrélés (météo, vacances, carburant, foot…) + verdict | forecasts |
| GET     | `/api/v1/forecasts/{id}/cross-product` | Produits substituts / compléments (effets croisés) | forecasts |
| GET     | `/api/v1/signals/definitions` | Registre des séries de signaux externes       | forecasts |
| GET     | `/api/v1/signals/observations`| Valeurs historiques d'une série (`?signal_key=`) | forecasts |
| POST    | `/api/v1/signals/ingest`      | Tire l'historique des signaux (idempotent)    | forecasts |
| POST    | `/api/v1/forecasts/recompute` | Relance prévisions + recos (job `recommend` tracé) | forecasts |
| GET     | `/api/v1/pipelines/runs`      | Runs de pipeline (filtrable job/statut)       | forecasts |
| GET     | `/api/v1/pipelines/runs/{id}` | Détail d'un run                               | forecasts |
| POST    | `/api/v1/pipelines/{job}/trigger` | Déclenche un job (manuel, human-in-the-loop) | forecasts |
| GET     | `/api/v1/pipelines/health`    | Fraîcheur + dernier run par job (Data Ops)    | forecasts |
| GET     | `/api/v1/recommendations`     | Recommandations explicables (persistées ou `?live=true`) | forecasts |
| POST    | `/api/v1/recommendations/simulate` | « Et si je commande X ? » (impact projeté) | forecasts |
| GET     | `/api/v1/alerts`              | Alertes décisionnelles (filtrable `?status=`) | forecasts |
| POST    | `/api/v1/alerts/{id}/resolve` | Résolution humaine (resolved/dismissed, auditée) | orders |
| GET     | `/api/v1/stream/events`       | Flux **SSE** temps réel, filtré par tenant    | (auth)    |
| POST    | `/api/v1/orders/{id}/approve` | Validation humaine d'une commande (auditée)   | orders    |
| GET     | `/api/v1/whatsapp/webhook`    | Handshake de vérification Meta                | —         |
| POST    | `/api/v1/whatsapp/webhook`    | Réception message → orchestrateur d'agents    | —         |
| POST    | `/api/v1/slack/webhook`       | Slack Events API (challenge + message → agents) | —       |

## Exemple — prévision

`GET /api/v1/forecasts/1?horizon_days=7`

```json
{
  "product_id": 1,
  "model": "naive",
  "horizon_days": 7,
  "points": [{ "ds": "2026-07-01", "yhat": 19.5, "yhat_lower": 15.6, "yhat_upper": 23.4 }],
  "explanation": "Moyenne mobile 28j ajustée par saisonnalité hebdo, jours fériés et fêtes."
}
```

## Exemple — facteurs de demande (corrélation, pas causalité)

`GET /api/v1/forecasts/1/factors`

```json
{
  "product_id": 1,
  "period_from": "2026-01-01",
  "period_to": "2026-06-30",
  "factors": [
    { "signal_key": "weather_temp_c", "label": "Température (°C)", "kind": "weather",
      "correlation": 0.62, "n": 120, "direction": "positive", "strength": "forte",
      "verdict": "corrélation probable (confirmer la causalité)",
      "explanation": "Température (°C) : corrélation positive r=0.62 sur 120 jours (...)." }
  ],
  "caveat": "Corrélation ≠ causalité : à confirmer par un test (A/B, hold-out) avant d'agir.",
  "explanation": "1 facteur(s) évalué(s) ... classés par force de corrélation."
}
```

## Exemple — webhook WhatsApp

`POST /api/v1/whatsapp/webhook` avec `{ "from": "+212...", "message": "passer une commande" }` :

```json
{
  "to": "+212...",
  "reply": "Je propose de commander ... Validez-vous ?",
  "agent": "agent_order",
  "requires_approval": true,
  "actions": [{ "type": "create_order", "payload": {}, "requires_approval": true }]
}
```
