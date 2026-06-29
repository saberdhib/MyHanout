# Socle retail générique — audit & architecture

> Réponse à la demande « base retail universelle, configurable par client ».
> Principe : **générique d'abord, paramétrable ensuite**. Aucun métier figé dans le
> socle ; les spécificités vivent dans la **config** (modules, profils, providers).
> Démo actuelle = alimentation générale / boucherie ; le même socle sert d'autres verticals.

## 1. Audit de l'existant (par bloc du cahier des charges)

Statut : ✅ existe · 🟡 partiel · ⛔ à faire · 🚫 hors-socle (raison produit)

| Bloc | Statut | Où / note |
|------|--------|-----------|
| **Caisse / ventes** | 🟡 | Ingestion ventes (POS connecteur, idempotent), historique ventes, CA via marges. **Manque** : écran caisse natif (ticket, scan, remise, retour) → priorité produit n°1. |
| **Catalogue produits** | ✅ | Produits (sku, prix, coût via factures, **famille**, catégorie, unité, actif), **historique prix**, recherche. Variantes = ⛔ (point d'extension). |
| **Stock / inventaire** | ✅ | Stock temps réel, entrées/sorties (fin de journée), **seuils & alertes rupture**, péremption, **lots viande** + traçabilité, chaîne du froid. |
| **Promotions / pricing** | ✅ | Remises promo, promo par produit, prix barré (affiche), **suggestions de déstockage** (anti-gaspi), suivi (audience). |
| **Fournisseurs / appro** | ✅ | Base fournisseurs, factures (historique d'achat), délai, **propositions de réassort**, génération de commande (3 modes). Comparaison prix = 🟡 (via historique). |
| **CRM / fidélisation** | 🟡 | Fiche client + consentement RGPD, diffusion opt-in (promo). **Manque** : segmentation auto (réguliers/perdus/nouveaux), offres perso. |
| **Dashboard** | ✅ | CA/marge/stock/alertes, top via marts dbt, signaux. Comparaison N-1 = 🟡. |
| **IA métier** | ✅ | Assistant conversationnel (NL), résumés, recommandations, messages promo, prévisions. |
| **Automatisation / alertes** | ✅ | Rupture, stock bas, marge faible, péremption, chaîne du froid, échéances. Rotation lente = 🟡. |

**Inutile / trop spécifique à ne PAS mettre en dur** (🚫) : règles fiscales par pays,
plans comptables certifiés, vocabulaire métier figé (coupes viande) → **points
d'extension** (config/alias par tenant), pas du socle.

## 2. Architecture générique (socle + extensions)

```
Socle (commun)                      Extension (par client / vertical)
─────────────────────              ──────────────────────────────────
modèles & API multi-tenant     →   profils (type de commerce) → modules actifs
providers ABC + mock           →   .env : quels providers réels (IA, POS, capteurs…)
modules (registry)             →   /config/modules : nav & features par commerce
données tenant (DB)            →   catalogue, prix, capteurs, clients du commerce
analytics (dbt/marts)          →   dashboards Grafana par commerce
```

- **Modules** : `backend/app/core/modules.py` (registry) + `GET /config/modules`.
  Un **profil** (boucherie, primeur, supérette, boulangerie…) active/désactive des
  modules ; profil inconnu = générique complet. Le frontend adapte la **navigation**.
- **Providers** : chaque intégration (IA, OCR, POS, capteurs, email, DWH) = ABC +
  **mock par défaut** ; le réel s'active par `.env`. Cf. `CLAUDE.md` §4.
- **Cœur vs mouvant** : `docs/configuration.md`.

### Couches
- **Écrans/nav** : pilotage, commerce, quotidien, données (filtrés par modules).
- **Modèles** : `backend/app/models/` (tous `TenantMixin` sauf référentiels globaux).
- **Services** : `backend/app/services/` (métier) ; `intelligence/` (IA) ; `ingestion/` (ETL).
- **API** : `backend/app/api/v1/`.
- **Analytics** : `analytics/` (dbt + Airflow), `docs/data-engineering.md`.
- **Config** : `.env`, `core/modules.py`, données tenant.

## 3. « Montrer qu'on fait autre chose » (sans refaire le socle)

1. Créer l'organisation avec un `business_type` (`primeur`, `boulangerie`, `superette`…).
2. `GET /config/modules` renvoie les modules adaptés → la nav change automatiquement
   (ex. `primeur` masque la Boucherie ; `magasin_specialise` masque aussi la chaîne du froid).
3. Brancher ses providers via `.env` (mock si rien). Aucune ligne de socle modifiée.

> Ajouter un vertical = une entrée dans `PROFILE_DISABLES` + éventuels libellés/unités.
> Pas de fork, pas de branche métier dans le code commun.

## 4. Mobile natif — recommandation

Aujourd'hui : **web responsive + PWA installable** (mobile/tablette de caisse,
hors-ligne léger). Pour une **vraie app native** (caisse terrain, scan code-barres,
offline robuste) :
- **Expo / React Native** (TypeScript), réutilisant l'API et les types existants.
- Module **Caisse** natif d'abord (priorité n°1) : ticket rapide, scan, paiement, offline + sync.
- Partage du design system (tokens de marque) et de la couche API (client typé).

C'est un **chantier dédié** : à lancer en repo/app séparé `mobile/` (Expo) qui
consomme le même backend. Recommandation : démarrer après stabilisation du module Caisse côté API.

## 5. Prochaines étapes de personnalisation par client
- Choisir le `business_type` (profil) → modules par défaut.
- Activer/désactiver des modules à la carte (futur : overrides par tenant).
- Brancher providers réels (IA, POS, capteurs) via `.env`.
- Charger le catalogue (import JSON/email/caisse) ; définir familles/unités.
- Importer dashboards Grafana ; planifier l'ELT (Airflow).

Voir : `docs/configuration.md`, `docs/roadmap.md`, `docs/ai-models.md`, `docs/data-engineering.md`.
