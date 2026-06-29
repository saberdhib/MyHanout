# Modèles IA, `.env` et MLOps

> À quoi sert chaque modèle, quelle variable d'environnement le pilote, et comment
> changer un paramètre **sans toucher au code**. Règle d'or : **sans clé → mock**.
> Tout tourne en local/CI sans aucune clé ; tu actives le réel quand tu veux.

## 1. Tableau des modèles / providers IA

| Capacité | Variable(s) `.env` | Options | Défaut | À quoi ça sert |
|----------|--------------------|---------|--------|----------------|
| **LLM** (rédaction, agents, Q&A) | `LLM_PROVIDER` | `mock` \| `claude` \| `mistral` \| `huggingface` | `mock` | Messages promo, réponses assistant, classification fine |
| ↳ Claude | `ANTHROPIC_API_KEY`, `LLM_MODEL` | clé + id modèle | — | LLM hébergé Anthropic |
| ↳ Mistral | `MISTRAL_API_KEY` | clé | — | LLM/OCR Mistral |
| ↳ HuggingFace | `HUGGINGFACE_API_KEY`, `HF_LLM_MODEL` | clé + repo | `mistralai/Mistral-7B-Instruct-v0.3` | LLM via Inference API |
| **Embeddings** (RAG) | `EMBEDDING_PROVIDER`, `HF_EMBEDDING_MODEL` | `mock` \| `huggingface` | `mock` / `sentence-transformers/all-MiniLM-L6-v2` | Vectorisation des factures pour le RAG |
| **Vector store** | `RAG_VECTOR_STORE`, `RAG_TOP_K` | `memory` \| `pgvector` | `memory` / `4` | Stockage/recherche vectorielle (pgvector en prod) |
| **Images** (affiches promo) | `IMAGE_PROVIDER`, `HF_IMAGE_MODEL` | `mock` \| `huggingface` | `mock` / `stabilityai/stable-diffusion-xl-base-1.0` | Génération d'affiches anti-gaspillage (text-to-image) |
| **OCR** (factures) | `OCR_PROVIDER`, `MISTRAL_API_KEY` | `mock` \| `mistral` \| `pdf_fallback` | `mock` | Lecture des factures (photo/PDF) |
| **Prévision demande** | `FORECAST_MODEL`, `FORECAST_HORIZON_DAYS` | `naive` \| `prophet` \| `lgbm` | `naive` / `14` | Prévision de ventes (réassort) |
| **Classifieur charges** | `FINANCE_CLASSIFIER` | `mock` \| `llm` | `mock` | Tagging OPEX/CAPEX des factures |

> Les autres providers (capteurs, caisse, email, DWH, WhatsApp, Telegram) suivent la
> même logique et sont documentés dans `docs/DEPLOY.md` et `.env.example`.

## 2. Quelles clés/modèles HuggingFace mettre (recommandations)

Tu as accès à HuggingFace → un seul `HUGGINGFACE_API_KEY` débloque LLM + embeddings + images :

```dotenv
HUGGINGFACE_API_KEY=hf_xxx
# LLM (rédaction promo, assistant) — bon rapport qualité/coût, multilingue FR :
LLM_PROVIDER=huggingface
HF_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
# Embeddings (RAG) — léger et rapide ; passe en pgvector pour la persistance :
EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_VECTOR_STORE=pgvector
# Affiches promo (text-to-image) :
IMAGE_PROVIDER=huggingface
HF_IMAGE_MODEL=stabilityai/stable-diffusion-xl-base-1.0
```

Alternatives utiles :
- LLM plus costaud : `meta-llama/Llama-3.1-8B-Instruct` (qualité ↑, coût ↑).
- Embeddings multilingues : `intfloat/multilingual-e5-large` (FR/AR ↑, dim ↑).
- Images plus rapides : `stabilityai/sdxl-turbo`.

> ⚠️ La dimension d'embedding est ramenée à `EMBED_DIM=1536` (padding/troncature)
> pour rester compatible `pgvector(1536)` — changer de modèle ne casse pas la base.

## 3. Changer un paramètre (sans code)

Tout est dans `.env` (lu par `app/config.py`, Pydantic Settings). Exemples :

| Besoin | Variable | Exemple |
|--------|----------|---------|
| Horizon de prévision | `FORECAST_HORIZON_DAYS` | `21` |
| Modèle de prévision | `FORECAST_MODEL` | `prophet` |
| Sensibilité alerte prix fournisseur | `FINANCE_PRICE_ANOMALY_PCT` | `0.15` (= +15 %) |
| Nb de passages RAG | `RAG_TOP_K` | `6` |
| Activer le tracing | `OTEL_ENABLED` | `true` |
| Rate limiting | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE` | `true`, `240` |

Après modif : redémarrer l'API (`make restart` ou `docker compose restart api`).

## 4. MLOps — boucle de qualité robuste

La prévision est **évaluée puis réentraînée**, de façon versionnée :

```
prévision (jour J) -> réel observé (J+n) -> écart -> MAE / MAPE -> réentraînement versionné
```

| Étape | Où | Endpoint |
|------|----|----------|
| Métriques (MAE/MAPE par produit/modèle) | `services/` + `forecast_evaluation` | `GET /mlops/metrics` |
| Réentraînement + versionnage | `services/` | `POST /mlops/retrain` |
| Évaluation routage des agents (golden set) | `intelligence/agents/` | `GET /agents/eval` |

Bonnes pratiques en place : modèles **abstraits + mock** (test sans dépendance),
métriques persistées (suivi dans le temps), réentraînement **déclenché par l'humain**
(pas de drift silencieux), signal d'apprentissage des **corrections** (ex. OPEX/CAPEX
dans `expense_classification_feedback`).

Roadmap MLOps (proposé) : registre de modèles (versions + métriques attachées),
détection de drift automatique, A/B des modèles de forecast, scheduling via Airflow.

## 5. Alimenter l'IA : sources & extension admin

Aujourd'hui, on alimente l'IA/les données par :
- **Import JSON** (`POST /import/json`) — catalogue, ventes, stock.
- **Email / drag&drop / WhatsApp** — factures (OCR).
- **Caisse (POS)** (`POST /import/pos/sync`).
- **RAG** — indexation des factures (`POST /rag/index/invoices/{id}`).

**Interface admin « ajouter une API / un fichier »** (proposé, voir roadmap) : une
page Admin où le propriétaire :
1. branche une **source HTTP** (URL + clé) mappée sur un provider (`http`),
2. **dépose un fichier** (CSV/JSON/PDF) qui atterrit dans la raw zone (MinIO) puis
   est ingéré,
3. choisit le **modèle IA** par capacité (sélecteur = écrit la variable `.env`/config tenant).

> Ce panneau s'appuie sur l'abstraction providers existante : « ajouter une API »
> = enregistrer une config de connecteur ; « ajouter un fichier » = upload → raw
> zone → pipeline d'ingestion. Rien de neuf côté philosophie, juste une UI.

## 6. Sécurité des secrets

- **Aucun secret dans le code** ni committé. Tout en `.env` (gabarit `.env.example`).
- En prod : gestionnaire de secrets (SSM / Secret Manager), jamais `.env` en repo.
- Les clés IA sont par déploiement ; une option future = clés **par tenant**
  (chiffrées) pour que chaque commerce branche les siennes.
