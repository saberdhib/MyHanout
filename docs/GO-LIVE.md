# 🚀 GO-LIVE — mettre ses clés API et en avant la musique

> **Tout fonctionne déjà sans aucune clé** (mode démo/mock, données fictives).
> Ce guide liste, capacité par capacité, la ou les variables `.env` à renseigner
> pour passer au **réel**. Une capacité sans clé retombe automatiquement en mock —
> rien ne casse jamais. Référence complète : `.env.example`, `docs/DEPLOY.md`,
> `docs/ai-models.md`.

## 0. Prérequis (une fois)
```bash
cp .env.example .env      # puis édite les valeurs ci-dessous
make up                   # postgres+pgvector, redis, api, worker, frontend
make migrate && make seed # schéma + données démo
```
⚠️ **En production, change impérativement** `SECRET_KEY` (JWT **et** chiffrement des
connecteurs par commerce en dépendent).

## 1. IA générative (LLM — chat, agents, classification)
| Variable | Valeur |
|---|---|
| `LLM_PROVIDER` | `claude` \| `mistral` \| `huggingface` (défaut `mock`) |
| `ANTHROPIC_API_KEY` / `MISTRAL_API_KEY` / `HUGGINGFACE_API_KEY` | ta clé |

## 2. OCR de factures
`OCR_PROVIDER=mistral` + `MISTRAL_API_KEY` (sinon `pdf` local ou `mock`).

## 3. Prévision (MLOps)
Fonctionne sans clé (`naive` in-process). Options :
- `FORECAST_MODEL=prophet|lgbm` (modèles avancés),
- `FORECAST_SERVICE_CLIENT=http` + `ML_SERVICE_URL` (service ML isolé `ml-service/`,
  fallback in-process automatique). Suivi : `GET /mlops/metrics`.

## 4. Affiches promo (text-to-image)
`IMAGE_PROVIDER=huggingface` + `HUGGINGFACE_API_KEY` (sinon affiche SVG mock).

## 5. Messagerie (par commerce OU globale)
**Self-service (recommandé)** : chaque commerce colle ses identifiants dans
l'app → *Connecteurs → Mes connexions* (secrets chiffrés). **Ou** en global `.env` :
- WhatsApp : `WHATSAPP_PROVIDER=business` + `WHATSAPP_ACCESS_TOKEN` +
  `WHATSAPP_PHONE_NUMBER_ID` + `WHATSAPP_VERIFY_TOKEN` + `WHATSAPP_APP_SECRET`
  (webhook : `/api/v1/whatsapp/webhook` — voir la marche à suivre Meta dans le chat/DEPLOY).
- Slack : `SLACK_PROVIDER=bot` + `SLACK_BOT_TOKEN` (Events → `/api/v1/slack/webhook`).
- Telegram : `TELEGRAM_PROVIDER=bot` + `TELEGRAM_BOT_TOKEN`.

## 6. Données entrantes
- Email→factures : `EMAIL_PROVIDER=imap` + `EMAIL_IMAP_HOST/USER/PASSWORD`.
- Caisse (POS) : `POS_CONNECTOR=http` + `POS_URL` (+ clé si besoin).
- Capteurs froid : `SENSOR_PROVIDER=http` + `SENSOR_HTTP_URL`.
- Signaux externes (météo…) : `SIGNALS_PROVIDER=http` + URL.
- Entrepôt (DWH) : `DWH_TARGET=http` + `DWH_URL`.

## 7. RAG / embeddings
`RAG_VECTOR_STORE=pgvector` (sinon memory) ; embeddings selon `EMBEDDING_PROVIDER`.

## 8. Ouverture (rien à configurer)
Clés API (`X-API-Key`) et webhooks sortants signés se créent **dans l'app**
(Connecteurs → Accès API) — aucun `.env` requis.

## 9. Vérifier que tout est branché
- Dans l'app : page **Connecteurs** (badges `connecté` / `démo` / `à configurer`).
- API : `GET /api/v1/config/connectors` (état sans secrets), `GET /health`.
- Cycle complet : `POST /api/v1/pipelines/daily/trigger` → briefing généré.

## 10. Onboarding utilisateur
À la première connexion, l'app affiche un **tour de bienvenue** (relançable dans
**Réglages**). Réglages : thème clair/sombre + langue FR/EN.
