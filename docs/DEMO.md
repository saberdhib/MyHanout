# 🎬 Script de démo — MyHanout AI (≈ 10 min)

> Objectif : montrer la **valeur** (anticipation, anti-gaspillage, temps gagné), le
> **contrôle humain** (human-in-the-loop), la **sécurité/RGPD**, et le côté
> **compagnon du quotidien** (WhatsApp + signaux météo/tendances).
> Tout tourne **sans aucune clé externe** (providers en mock).

## 0. Préparation (1 min)
```bash
cp .env.example .env
docker compose up -d --build      # postgres+pgvector, redis, api, worker, frontend
make seed                         # org démo (épicerie) : produits + ventes + 1 périssable + clients opt-in
make seed-demo                    # ⭐ mode démo blindé : une boucherie fictive sur 3 mois
```
- Dashboard : http://localhost:5173  ·  API/Swagger : http://localhost:8000/docs
- Login démo : `admin@myhanout.example` / `admin` (auto-login en dev).

### ⭐ Mode démo blindé (`make seed-demo`)
Charge **d'une seule commande** une boucherie fictive complète (`boucher@myhanout.example` /
`admin`) : ~14 produits réalistes, **90 jours de ventes saisonnières** (pic week-end, lundi
fermé), stocks bas → alertes de réassort, lots en fin de vie → **démarques** (dont 2 déjà
appliquées → cash récupéré visible dans **Impact**), factures fournisseurs à échéances
étalées → **échéancier & trésorerie**, clients fidèles + **réservations** click&collect
(collectée/confirmée/en attente), recette merguez → **production**, frigos + capteur en
dérive → **chaîne du froid**, et le **briefing du jour** consolidé. Objectif : **toutes les
pages s'allument** sans aucune saisie manuelle devant le commerçant. Idempotent, 100 % fictif,
zéro clé externe. Données isolées de l'org « demo » (SKU préfixés `BCHD-`).

## 1. Le tableau de bord vivant (1 min)
- KPIs (références, alertes, factures, **MAPE** qualité prévision) + **signaux du jour**
  (météo + tendances → « forte demande boissons » / « barbecue »).
- Page **Prévisions** : courbe de demande par produit (pics vendredi/samedi).
- Message clé : *« l'IA lit vos données et anticipe. »*

## 2. Le moment « valeur » : promo flash anti-gaspillage (2 min)
- Page **Promos flash** → **« Scanner les fins de vie »**.
- L'IA détecte le périssable qui périme dans 2 jours → propose une **promo explicable**
  (le « pourquoi » : fin de vie + météo + tendance) — **en brouillon, pas envoyée**.
- Le commerçant clique **Publier** → diffusion **réseaux** + **clients opt-in**.
- Message clé : *« viande/pommes en fin de vie → 💥 promo ciblée en 1 clic, et c'est VOUS qui validez. »*

## 3. Sécurité & RGPD (1 min)
- La promo n'a été envoyée **qu'aux clients ayant consenti** (opt-in horodaté) — le client
  « Hassan » (sans consentement) n'a rien reçu.
- **Aucune action sortante sans validation humaine** ; tout est **audité** (`audit_log`).
- **Isolation multi-commerces** : chaque commerce ne voit que ses données (garde-fou central).
- Message clé : *« privacy-by-design : on ne diffuse qu'avec consentement, et vous gardez la main. »*

## 4. Le compagnon WhatsApp (2 min)
> Le webhook accepte un payload simplifié pour la démo (pas besoin de Meta) :
```bash
# Suggestion de commande conversationnelle
curl -s localhost:8000/api/v1/whatsapp/webhook -H 'content-type: application/json' \
  -d '{"from":"+212600000010","message":"commande pour demain"}' | jq .replies[0].reply
# Le commerçant valide
curl -s localhost:8000/api/v1/whatsapp/webhook -H 'content-type: application/json' \
  -d '{"from":"+212600000010","message":"oui"}' | jq .replies[0].reply
# Saisie de fin de journée
curl -s localhost:8000/api/v1/whatsapp/webhook -H 'content-type: application/json' \
  -d '{"from":"+212600000010","message":"stock BOEUF-HACHE 3 12"}' | jq .replies[0].reply
# Une PHOTO de facture (image) -> pipeline OCR -> facture en revue
curl -s localhost:8000/api/v1/whatsapp/webhook -H 'content-type: application/json' \
  -d '{"from":"+212600000010","image_id":"MEDIA-1"}' | jq .replies[0].reply
```
- Même cerveau dans le **chat web** (page **Assistant**).
- Message clé : *« zéro app à installer : WhatsApp suffit, et le dashboard pour aller plus loin. »*

## 5. Apprentissage (MLOps) & explicabilité (1 min)
- Chaque saisie réelle → **écart prévu/réel** (page **Qualité**, MAE/MAPE) → le modèle s'améliore
  (réentraînement versionné `naive-v1`).
- **RAG factures** : `POST /rag/index/invoices/{id}` puis `POST /rag/query {"question":"..."}`
  → réponse **citée** sur ses propres documents.

## 6. Le pitch business (1 min)
- **Pricing humain** : pas de coupure brutale en cas d'impayé → période de grâce (2-3 mois),
  puis possibilité de **rétrograder** à « stockage + requêtes » à petit prix (cf.
  [privacy-pricing.md](delivery/privacy-pricing.md)).
- Déploiement : `docker compose up` aujourd'hui ; cible cloud + DWH documentée.

---

## Mock vs réel (transparence)
| Bloc | Démo (défaut) | Réel (avec clé/config) |
|------|---------------|------------------------|
| OCR | mock (facture exemple) | Mistral OCR (`OCR_PROVIDER=mistral`) |
| LLM | mock déterministe | Claude/Mistral |
| WhatsApp | mock (journalisé) + payload simplifié | Business API (`WHATSAPP_PROVIDER=business`) |
| Météo / tendances | mock déterministe | API météo / veille sociale |
| Publication réseaux | mock (journalisé) | connecteurs réseaux |
| Vector store (RAG) | in-memory | pgvector (`RAG_VECTOR_STORE=pgvector`) |

## Prochaines briques (post-démo)
- Connecteurs réels : POS, compta, **DWH sync** (export `/data` → entrepôt), Telegram.
- Agent publication réseaux réel + comptes clients self-service.
- Forecasting Prophet/LightGBM + météo/promos comme régresseurs.
- Enforcement du billing (grâce/rétrogradation) — modélisé, non bloquant par design.
