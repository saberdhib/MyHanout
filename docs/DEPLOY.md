# 🚀 Déploiement — MyHanout AI

## Local / démo (mock, sans clé)
```bash
cp .env.example .env
docker compose up -d --build      # postgres+pgvector, redis, api, worker, frontend (dev)
make seed
# Dashboard http://localhost:5173 · API http://localhost:8000/docs
```

## Production (frontend buildé + nginx)
```bash
cp .env.example .env              # puis renseigner les VRAIES clés (voir tableau)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api python -m app.db.seed   # optionnel (données démo)
# Frontend http://localhost:8080  · API http://localhost:8000
```
- `api` applique les migrations Alembic au démarrage (`alembic upgrade head`).
- `frontend` est buildé statiquement et servi par nginx, qui **proxy `/api`** vers l'API.
- Redémarrage automatique (`restart: unless-stopped`), 2 workers uvicorn.

## Activer les fonctions réelles (mets tes clés dans `.env`)
| Variable | Effet | Activation |
|----------|-------|------------|
| `HUGGINGFACE_API_KEY` | LLM + embeddings réels (HF Inference) | `LLM_PROVIDER=huggingface`, `EMBEDDING_PROVIDER=huggingface` |
| `HUGGINGFACE_API_KEY` (+ `HF_IMAGE_MODEL`) | **Affiches promo** générées (text-to-image) | `IMAGE_PROVIDER=huggingface` |
| `ANTHROPIC_API_KEY` | LLM Claude | `LLM_PROVIDER=claude` |
| `MISTRAL_API_KEY` | OCR Mistral réel | `OCR_PROVIDER=mistral` |
| `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business réel | `WHATSAPP_PROVIDER=business` |
| `WHATSAPP_APP_SECRET` | Vérif signature webhook Meta | renseigner |
| `TELEGRAM_BOT_TOKEN` | Telegram réel | `TELEGRAM_PROVIDER=bot` |
| `EMAIL_IMAP_HOST` + `EMAIL_IMAP_USER` + `EMAIL_IMAP_PASSWORD` | **Import factures par email** (IMAP) | `EMAIL_PROVIDER=imap` |
| `DWH_URL` | **Sync entrepôt de données** (POST snapshot) | `DWH_TARGET=http` |
| `RAG_VECTOR_STORE=pgvector` | RAG persistant (pgvector) | (pg déjà en place) |
| `SECRET_KEY` | **À changer** (signature JWT) | obligatoire en prod |

> Tout est **optionnel** : sans clé, le provider correspondant retombe sur le mock.
> Le défaut reste donc fonctionnel et démontrable sans aucune dépendance externe.

## Webhooks (exposer l'API en HTTPS)
- WhatsApp : configurer l'URL `https://<host>/api/v1/whatsapp/webhook` (+ `WHATSAPP_VERIFY_TOKEN`).
- Telegram : `curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<host>/api/v1/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>"`.
- En local : utiliser un tunnel (ngrok/cloudflared) vers le port 8000.

## Cibles cloud
- Conteneurs managés (ECS/Cloud Run/Fly), **PostgreSQL managé + pgvector**, Redis managé.
- Secrets via gestionnaire (SSM / Secret Manager) — ne jamais committer `.env`.
- CI/CD : GitHub Actions (lint + typecheck + tests + build images + intégration pg).

## Livraison continue (images GHCR)
Le workflow `.github/workflows/cd.yml` **construit et pousse** les images vers le
GitHub Container Registry :
- push sur `main` → `ghcr.io/<owner>/myhanout-{backend,frontend,ml-service}:main` + `:sha-<court>`
- tag `vX.Y.Z`   → `:X.Y.Z` + `:latest` (release)

Déploiement (opéré côté infra, non automatisé ici pour rester agnostique) :
```bash
docker pull ghcr.io/<owner>/myhanout-backend:main   # ou :vX.Y.Z
# puis rollout sur la cible (compose/k8s/Cloud Run) avec le .env de prod.
```
Prérequis prod avant rollout : `SECRET_KEY` aléatoire (>=32c, sinon l'API refuse de
démarrer), `alembic upgrade head` (applique la RLS `0025`), `ML_INTERNAL_KEY` si
`FORECAST_SERVICE_CLIENT=http`.
