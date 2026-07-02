# Audit « prêt pour la prod & vendable » — MyHanout AI

> Audit basé sur l'inspection du code réel (pas théorique). Gravité :
> 🔴 critique (bloquant vente/prod) · 🟠 important · 🟡 souhaitable.
> Chaque point est **corrigeable** ; voir la feuille de route en fin de doc.

## Ce qui est DÉJÀ solide (à valoriser commercialement)
- **Multi-tenant** : garde-fou central (ContextVar + `with_loader_criteria` sur tous les
  SELECT ORM + estampillage à l'INSERT). Test d'isolation A≠B.
- **Sécurité de base** : JWT access/refresh, bcrypt, RBAC par rôle, middleware d'**audit**,
  **rate limit**, **tracing** (corrélation logs), **métriques** Prometheus, secrets
  connecteurs **chiffrés** (Fernet).
- **CI** : 7 jobs (lint/type/tests, intégration pg16+pgvector, front, vitrine, ml-service,
  E2E Playwright, build images Docker).
- **MLOps** : `model_version` partout, service ML isolé + **fallback in-process**,
  `/mlops/metrics`, `forecast_evaluation`, alerte `forecast_drift`.
- **Providers mock-first keyless** : zéro clé pour démarrer, réel par `.env`.

---

## 🔴 CRITIQUE — à corriger avant de vendre

### C1. Pas de plan « super-admin / plateforme » (le cœur du SaaS que tu décris) ✅ FAIT (Lot 2)
Tout est tenant-scopé : **il n'existe aucun moyen pour TOI de gérer l'ensemble des
clients**. C'est l'architecture inverse du garde-fou tenant, donc à concevoir
explicitement (cf. §« Plateforme SaaS » plus bas). Sans ça, pas d'« agent-as-a-service ».
→ Plan plateforme livré : `platform_admin` + `subscription` + `organization.status`
(migration 0023), auth cross-tenant **vérifiée en base + auditée**
(`core/platform_auth.py`), service `platform_service.py` (vue 360, provisioning,
suspension, billing), API owner-only `api/v1/platform.py`. Suspension d'un commerce =
blocage immédiat de ses utilisateurs (`_ensure_org_active`). Impersonation auditée :
prévue Lot 3.

### C2. `SECRET_KEY` par défaut `"change-me"`, sans garde au démarrage ✅ FAIT (Lot 1)
JWT **et** chiffrement des connecteurs en dépendent. Un déploiement qui oublie de la
changer = tokens forgeables + secrets déchiffrables. **Fix** : refuser de démarrer en
`ENV=production` si `SECRET_KEY` est la valeur par défaut (ou < 32 chars).
→ `Settings._enforce_prod_secret` (validator Pydantic) dans `backend/app/config.py`.

### C3. ml-service **sans authentification** ✅ FAIT (Lot 1)
`ml-service/` expose `/predict` sans aucun contrôle. En interne c'est tolérable, mais
dès qu'il est déployé (réseau, k8s), n'importe qui peut l'appeler. **Fix** : secret
partagé `X-Internal-Key` entre backend et ml-service.
→ `require_internal_key` (dépendance FastAPI) sur `/train` + `/predict`, en-tête posé
côté client dans `service_client.py`. `ML_INTERNAL_KEY` vide = keyless (local/CI).

### C4. Pas de scan sécurité dans la CI ✅ FAIT (Lot 1)
Aucun `pip-audit` / `bandit` / `trivy` (images) / `gitleaks` (secrets) / Dependabot.
Pour un produit qui manipule données commerçants + secrets, c'est un prérequis de
confiance (et souvent exigé en due diligence). **Fix** : ajouter un job `security`.
→ Job `security` dans `.github/workflows/ci.yml` : `pip-audit`, `bandit -r app`, gitleaks.

## 🟠 IMPORTANT — pour « scalable & pro »

### H1. Pas d'en-têtes de sécurité HTTP ✅ FAIT (Lot 1)
Manque CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
**Fix** : middleware `SecurityHeaders` (quelques lignes).
→ `SecurityHeadersMiddleware` (`backend/app/core/security_headers.py`), câblé dans
`main.py` ; HSTS ajouté hors `ENV=local`.

### H2. Isolation tenant uniquement applicative (pas de RLS Postgres) ✅ FAIT (Lot 4)
Le garde-fou ORM est bon mais **une requête SQL brute ou un bug de code contourne
l'isolation**. Le standard « pro » multi-tenant = **Row-Level Security Postgres**
(defense-in-depth) : `SET app.current_org` + policies `USING (organization_id = ...)`.
**Fix** : migration activant RLS + set du GUC par requête. (Gros, mais argument de vente.)
→ Migration `0025` : `ENABLE`+`FORCE ROW LEVEL SECURITY` + policy `tenant_isolation` sur
les **35 tables tenant** (GUC vide = accès plateforme/seed). GUC posé par `core/rls.py`
(`set_session_org`) à l'auth ; réinitialisé par requête (`get_session`). Test d'intégration
pg : `test_rls_blocks_raw_sql_cross_tenant` (SQL brut cross-tenant bloqué + WITH CHECK).

### H3. Index composites tenant manquants ✅ FAIT (Lot 1)
Le garde-fou filtre par `organization_id` sur **chaque** requête, mais les index sont
souvent sur la seule FK. **Fix** : index `(organization_id, <colonne chaude>)` sur les
tables volumineuses (sale, stock, invoice, temperature_reading, recommendation…).
→ Migration `0022_tenant_composite_indexes` (7 index composites, réversible).

### H4. JWT non révocable
Refresh tokens stateless, pas de rotation ni de blocklist. Impossible de déconnecter
un appareil volé ou de couper un client suspendu **immédiatement**. **Fix** : table
`refresh_session` (jti + révocation) ou short-TTL + rotation.

### H5. CD absent
La CI **build** les images mais ne les **pousse ni ne déploie** (pas de registry, pas
de tag versionné, pas de release). **Fix** : job qui tag `ghcr.io/.../backend:{sha}` +
`:latest` sur `main`, + workflow de release.

### H6. Cohérence doc ↔ réalité (Airflow)
La doc mentionne **Airflow** ; la réalité = orchestration **Celery + PipelineRun**
(très bien à cette échelle). À aligner dans la doc pour ne pas survendre / créer
d'attentes fausses en due diligence.

### H7. ml-service : pas de registry de modèles ni de ré-entraînement planifié ✅ FAIT (Lot 5)
`prophet`/`lgbm` sont calculés à la volée. Pour du « vrai MLOps » : persister les
modèles (artefacts versionnés, ex. MinIO déjà présent), ré-entraînement planifié,
et **retrain déclenché par la dérive** (l'alerte existe déjà, pas l'action).
→ Registre `model_artifact` (migration 0026, versionné, 1 actif/produit, métriques +
déclencheur). `services/model_registry_service.py` : retrain manuel/planifié/dérive.
Job pipeline `retrain` (planifié) + alerte `forecast_drift` émise dans `scan_alerts`
+ `retrain_on_drift`. API `/mlops/models`, `/mlops/retrain` (versionne). Front : registre
dans Data Ops. `artifact_uri` prêt pour la sérialisation MinIO (prophet/lgbm).

## 🟡 SOUHAITABLE (Lot 6 — largement traité)
- ✅ Backups pg : `scripts/backup_pg.sh` (dump + rétention) + procédure de test de restore
  documentée (`docs/DEPLOY.md`). Planification cron/systemd côté infra.
- ✅ Limite de taille des uploads (OCR/factures) : `MAX_UPLOAD_MB` → 413 (`core/uploads.py`).
- ✅ Pagination bornée : `core/pagination.py` (`MAX_PAGE_SIZE`), appliquée aux listes
  (alerts, registre de modèles…). Reste à étendre au fil de l'eau aux listes restantes.
- ✅ Erreurs centralisées : Sentry optionnel (`SENTRY_DSN`, soft-import). ✅ Alerting Grafana :
  service Prometheus (scrape `/metrics`) + datasource + **règles provisionnées**
  (`analytics/grafana/provisioning/alerting/rules.yml` : échecs pipeline, taux 5xx) +
  alerte applicative `forecast_drift`. Reste (spécifique client) : le *contact point*
  (Slack/email) de notification.
- ✅ Idempotence webhooks entrants (WhatsApp/Slack) : dédup par `external_id`/`event_id`
  (table globale `webhook_inbound`, migration 0027, `messaging/idempotency.py`).

**Reliquat Lot 5 traité** : sérialisation des artefacts de modèles via `ArtifactStore`
(mock keyless par défaut, MinIO en option) — `intelligence/mlops/storage.py`,
`artifact_uri` renseigné à chaque enregistrement.

---

## 🏢 La plateforme SaaS que tu veux (backoffice + self-service)

Deux plans clairement séparés :

### Plan CLIENT (existe déjà en grande partie ✅)
Le commerçant gère **son** commerce : ses connexions (WhatsApp/caisse/…, modèle B
chiffré ✅), ses réglages (thème/langue ✅), ses agents, ses données. Manque côté client :
- **Support** : ouvrir un ticket depuis l'app.
- **Facturation/abonnement** : voir son plan, son usage, ses factures.
- **Nouveautés** : changelog in-app (« quoi de neuf »).

### Plan PLATEFORME (à construire — c'est le gros morceau 🔴)
Un **espace admin MyHanout** qui opère **au-dessus** des tenants :
1. **Compte plateforme** : `PlatformAdmin` (utilisateur MyHanout, hors org client) +
   auth/scope dédié + **garde-fou relâché de façon explicite et auditée** (le seul
   endroit qui voit tous les tenants).
2. **Cycle de vie client** : modèle `Subscription`/`Plan` (trial/active/suspended/
   churned), statut d'org, dates, MRR. Suspendre un client = couper l'accès (lié à H4).
3. **Vue 360 par client** : santé (pipelines OK ?, dernière activité, erreurs),
   **usage** (nb produits, ventes ingérées, messages, appels API), conformité clé.
4. **Tickets & support** : modèle `SupportTicket` (client ↔ MyHanout), statut, priorité,
   fil de messages. Côté client : bouton « Aide » ; côté plateforme : file de tickets.
5. **Mises à jour & correctifs** : `ReleaseNote`/changelog versionné, bannière in-app
   « nouveauté », + le CD (H5) pour livrer les correctifs proprement.
6. **Provisioning** : créer un nouveau client (org + owner + plan) en 1 clic depuis le
   backoffice → onboarding automatique.
7. **Impersonation auditée** : « voir comme ce client » pour le support (trace obligatoire).

> ⚠️ Sécurité : ce plan plateforme est **la** surface la plus sensible. Chaque accès
> cross-tenant doit être tracé (audit), borné par un rôle plateforme, et idéalement
> derrière une auth renforcée (2FA). C'est aussi pour ça que **RLS (H2)** devient
> important : le plan client ne doit JAMAIS pouvoir atteindre un autre tenant, seul le
> plan plateforme le peut, explicitement.

---

## Feuille de route proposée (ordre de valeur)

**Lot 1 — Durcissement sécurité (rapide, forte confiance) 🔴🟠 ✅ FAIT**
C2 (garde SECRET_KEY) + C3 (auth ml-service) + C4 (job CI sécurité) + H1 (headers) +
H3 (index composites). ~1 brique, peu de risque, énorme gain de crédibilité.

**Lot 2 — Fondation plateforme (le backoffice) 🔴**
Compte `PlatformAdmin` + garde-fou cross-tenant audité + modèles `Subscription`/statut
d'org + vue 360 clients + provisioning. C'est le socle « agent-as-a-service ».

**Lot 3 — Support & mises à jour 🟠 ✅ FAIT**
`SupportTicket` (client + backoffice) + `ReleaseNote`/changelog in-app.
→ Tickets tenant (`support_ticket`/`support_message`) : le commerçant ne voit que les
siens (garde-fou), l'opérateur les voit tous (cross-tenant audité). Changelog produit
global (`release_note`, publié → visible commerces). Migration 0024. API `support.py`
(commerçant) + section `platform.py` (opérateur). Front : page `Support.tsx` +
backoffice enrichi. Impersonation auditée : toujours en option (non implémentée).

**Lot 4 — RLS Postgres (defense-in-depth) 🟠 ✅ FAIT**
Migration RLS + GUC par requête + tests. Argument de vente « isolation garantie DB ».
→ Migration 0025 (35 tables), `core/rls.py`, test d'intégration pg.

**Lot 5 — CD + MLOps avancé 🟠🟡 ✅ FAIT**
CD : `cd.yml` (build+push GHCR sur main/tags). MLOps : registre `model_artifact` (0026),
retrain planifié/dérive, alerte `forecast_drift`. Reste optionnel : sérialisation réelle
des artefacts prophet/lgbm dans MinIO (le champ `artifact_uri` est prêt).

**Détail initial ↓**
Registry/tags images + release ; registry de modèles + retrain déclenché par dérive.

**Lot 6 — Finitions 🟡**
Backups/restore, limites d'upload, pagination, alerting Grafana, Sentry.

> Chaque lot garde les règles d'or : mock-first, gate vert, migrations réversibles,
> tout tracé/expliqué, aucun secret en dur.
