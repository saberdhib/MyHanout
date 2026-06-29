# API Design — MyHanout AI

API REST FastAPI, versionnée sous `/api/v1`. Doc interactive : `/docs` (Swagger).

## Conventions

- **Versioning** par préfixe d'URL (`/api/v1`).
- **Réponses listes** : `{ "items": [...], "total": n }` (`ListResponse[T]`).
- **Erreurs** : `{ "error": { "code": "...", "message": "..." } }` (cf. `core/exceptions.py`).
- **Auth/RBAC** : dépendance `require_permission(scope)`. MVP : utilisateur de dev
  (`core/security.DEV_USER`) ; auth par token à implémenter.
- **Audit** : middleware trace toutes les requêtes mutantes ; actions sensibles
  persistées dans `audit_log`.

## Endpoints (MVP)

| Méthode | Chemin                         | Description                                   | Scope     |
|---------|--------------------------------|-----------------------------------------------|-----------|
| GET     | `/health`                      | Healthcheck                                   | —         |
| GET     | `/metrics`                     | Métriques Prometheus                          | —         |
| GET     | `/api/v1/auth/me`              | Utilisateur courant                           | —         |
| GET     | `/api/v1/stocks`              | Liste des stocks (+ nom produit)              | stocks    |
| GET     | `/api/v1/stocks/alerts`       | Stocks sous le seuil de réassort              | stocks    |
| GET     | `/api/v1/invoices`            | Factures + lignes                             | invoices  |
| GET     | `/api/v1/forecasts/{id}`      | Prévision de demande d'un produit             | forecasts |
| POST    | `/api/v1/orders/{id}/approve` | Validation humaine d'une commande (auditée)   | orders    |
| GET     | `/api/v1/whatsapp/webhook`    | Handshake de vérification Meta                | —         |
| POST    | `/api/v1/whatsapp/webhook`    | Réception message → orchestrateur d'agents    | —         |

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
