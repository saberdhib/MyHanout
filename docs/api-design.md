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
| GET     | `/api/v1/auth/me`              | Utilisateur courant                           | (token)   |
| POST    | `/api/v1/invoices/upload`     | Importe un document → facture `pending_review`| invoices  |
| POST    | `/api/v1/invoices/{id}/approve`| Validation humaine → écrit les lignes + audit | invoices  |
| POST    | `/api/v1/invoices/{id}/reject`| Rejet humain avec motif (audité)              | invoices  |
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
