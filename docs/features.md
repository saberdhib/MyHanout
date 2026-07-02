# MyHanout AI — Catalogue des fonctionnalités

> Vue d'ensemble regroupée par domaine. Tout est **multi-tenant**, **human-in-the-loop**,
> **explicable** et **mock-first / keyless** (fonctionne sans aucune clé en démo).

## 🤖 IA & système multi-agents
- **Équipe d'agents spécialisés** (`intelligence/agents/`, orchestrateur d'intentions) :
  Réassort, Stock, Finance, Marketing/Promo, **Démarque**, **Production**,
  **Tâches du jour (briefing)**, Gouvernance (garde-fou), Support (conversationnel).
- **Briefing du matin** : consolidation proactive (alertes + réassort + démarque +
  production) en tâches priorisées, cochables, poussées sur WhatsApp/Slack.
- **Agent Démarque (anti-gaspi frais)** : remise optimale par lot selon DLC & écoulement
  (cash récupéré vs perte sèche), explicable.
- **Agent Production & recettes** : combien fabriquer (dérivé du forecast, arrondi au
  rendement) + nomenclature → besoins ingrédients & coût.
- **Agent Bilan hebdo** : CA vs S-1, marge, top ventes, démarque récupérée → 3 actions.
- **Agents conseil Prix & Effectifs** : prix cible (marge + arrondi psychologique, jamais
  sous le coût), renfort staff selon l'affluence prévue par jour.
- **Agent Relance client** : segmentation (récompense prête / presque / inactif) + message.
- **Réassort explicable** : moteur de règles pur (quoi/combien/quand commander), simulation
  « et si je commande X ? ».
- **Gouvernance human-in-command** : toute action sortante validée par un humain + audit.
- **Explicabilité systématique** : chaque suggestion/prévision porte sa raison + sa confiance.
- **Providers LLM abstraits** (mock | claude | mistral | huggingface), **RAG** (embeddings +
  vector store memory/pgvector), **génération d'affiches promo** (text-to-image, SVG mock).
- **Classifieur de dépenses** OPEX/CAPEX (mock | llm).

## 🔮 Prévision & MLOps
- **Modèles** : naïf (défaut) | Prophet | LightGBM, `model_version` traçable.
- **Service ML isolé** (`ml-service/`, auth `X-Internal-Key`) avec **fallback in-process**.
- **Registre de modèles versionné** (`model_artifact`) : 1 version active par produit +
  métriques (MAE/MAPE) + déclencheur (manuel / planifié / **dérive** / seed).
- **Boucle de dérive** : MAPE > seuil → alerte `forecast_drift` → **ré-entraînement auto**.
- **Artefacts** sérialisés via `ArtifactStore` (mock keyless | MinIO S3).
- **Signaux externes** (météo, vacances, paie, matchs, prix carburant…) + **signaux métier**
  du commerçant (braderie, jour de paie…), croisés avec les ventes.
- **Analyse de corrélation** (Pearson, verdict prudent) + **effets cross-produit**.
- **Détection de saisonnalité** et tampon de sécurité paramétrable.

## 🗄️ Data & ingestion
- **OCR de factures** (mock | mistral | pdf) → parsing → validation → ETL, idempotent par hash.
- **Import factures par email** (IMAP), **import JSON**, **sync entrepôt de données (DWH)**.
- **Connecteur caisse (POS)** : ingestion des ventes (idempotent par référence).
- **Capteurs chaîne du froid (IoT)** : relevés de température (mock déterministe).
- **Orchestration de pipelines** (`PipelineRun` tracé, Celery) : jobs = suites d'assets
  (snapshot stock, signaux, réassort, alertes, briefing) ; cycle **quotidien**.
- **Socle data engineering** : dbt, Airflow, Grafana, MinIO (`docker-compose.data.yml`).
- **Snapshots d'inventaire**, **historique des prix** (achat/vente) traçé.

## 📊 Dashboard & app (frontend)
- **Tableau de bord** : KPIs (CA, marge, ruptures évitées, stock à risque), graphiques
  (sans dépendance), répartition des ventes.
- **Pages** : Briefing, Bilan hebdo, Recommandations, Alertes, Démarque, Production,
  Prix conseillés, Effectifs, Prévisions, Stocks, Catalogue, Boucherie, Promos, Fidélité,
  Relance client, Réservations, Finance, Échéancier, Contrôles & pertes, Factures,
  Fournisseurs, Fin de journée, Qualité, Chaîne du froid, Hygiène (HACCP), Data Ops,
  Connecteurs, Intégrations, Aide & support, Backoffice (opérateur), Assistant (chat).
- **Temps réel (SSE)** filtré par tenant + repli polling.
- **Fenêtre de chat flottante** (assistant IA) montée dans tout le shell.
- **PWA installable** + responsive (mobile/desktop), dark mode, thème de marque.
- **Socle retail modulaire** : la navigation s'adapte au **type de commerce**
  (boucherie, épicerie, primeur, boulangerie, supérette…).

## 🏪 Métier (modules retail)
- **Catalogue & prix** : produits, familles, prix, historique. **Prix conseillés** & **Effectifs**.
- **Stock & inventaire** : niveaux, seuils, **péremption (DLC)**.
- **Boucherie** : lot → coupes, rendement, coût/kg, traçabilité.
- **Finance** : pré-compta (OPEX/CAPEX), trésorerie, marges, alertes financières,
  **échéancier fournisseurs + trésorerie prévisionnelle 4 semaines**.
- **Contrôles & pertes** : 3-way match factures + démarque inconnue (valorisée).
- **Hygiène (HACCP)** : plan de nettoyage tracé + conformité froid + registre.
- **Chaîne du froid** : équipements, températures, conformité, alertes.
- **Promotions** : promos flash explicables + affiches IA.
- **Démarque, Production, Recettes** (cf. IA).
- **Fidélité client** : points explicables + récompenses (grand livre, HITL).
- **Relance client ciblée** : campagnes opt-in (RGPD) via WhatsApp, remontées au briefing.
- **Réservations (click & collect)** : cycle demande→prête→récupérée, points au retrait,
  réservation aussi **via WhatsApp**.
- **Clients / CRM** léger (opt-in RGPD), **fin de journée**, **qualité (écarts)**.
- **Alertes** : ruptures, péremption, dérive forecast, données obsolètes, finance.

## 💬 Conversationnel & connecteurs
- **WhatsApp** (mock | Business API), **Telegram** (mock | bot), **Slack** (mock | bot +
  Events API), **chat web**.
- **Parcours WhatsApp** : réassort fournisseur (validé), saisie stock, photo de facture (OCR),
  **réservation client**, Q&A agents. **Idempotence** des webhooks entrants (dédup event id).
- **Connecteurs par commerce (self-service, modèle B)** : chaque commerce branche SES accès
  (secrets **chiffrés**), résolveur tenant-aware. **État sans secret** (`/config/connectors`).

## 🔌 Ouverture & interopérabilité
- **Clés API** (`X-API-Key`, hash + préfixe, scopes RBAC) — accès programmatique
  (n8n / Make / Zapier / scripts).
- **Webhooks sortants signés HMAC** (`alert_created`, `pipeline_finished`).
- **Import/export** JSON & DWH. (MCP serveur : prévu, non encore implémenté.)

## 🛰️ Backoffice plateforme (SaaS, agent-as-a-service)
- **Plan cross-tenant** pour l'opérateur MyHanout (l'inverse du garde-fou), **audité** :
  vue 360 clients, MRR/ARR, provisioning d'un commerce, suspension/réactivation, plans.
- **Cycle de vie commerce** (`active`/`trial`/`suspended`/`cancelled`) : une suspension
  bloque immédiatement les utilisateurs du commerce.
- **Support** : tickets tenant (le commerçant voit les siens, l'opérateur tous) + **changelog
  produit** publié in-app.

## 🔒 Sécurité, multi-tenant & conformité
- **Isolation multi-tenant centrale** : org du token JWT (jamais d'un param client),
  filtrage automatique de tous les SELECT ORM, estampillage des INSERT.
- **Defense-in-depth : RLS Postgres** (`FORCE`) — l'isolation tient même en SQL brut.
- **Durcissement** : garde `SECRET_KEY` en prod, en-têtes HTTP de sécurité, auth ml-service,
  limite d'upload, pagination bornée, scan CI (pip-audit / bandit / gitleaks).
- **RBAC** par rôle (owner/manager/staff/accountant/viewer) + scopes.
- **Audit** de toute action sortante ; **RGPD** (opt-in, données démo fictives).
- **Aucun secret en dur** : `.env` only, fallback mock sans clé.

## 🧱 Qualité & ops
- **Gate** : ruff + black + mypy + pytest (sqlite rapide + marqueur pg d'intégration).
- **Tests E2E** Playwright, **CI** multi-jobs (backend, pg, frontend, website, ml-service,
  e2e, docker, **sécurité**), **CD** : build + push images GHCR (`:main`/`:sha`/`:version`).
- **Observabilité** : health étendu, métriques Prometheus + **règles Grafana** provisionnées,
  Sentry optionnel. **Backups pg** (script + test de restore documenté).
- **Migrations** Alembic linéaires & réversibles.

## 🌐 Vitrine (site public)
- Site **Astro** statique (SEO) séparé de l'app : pages /, /pricing, /contact, /confiance,
  section « Comment on opère » (architecture + accompagnement), tokens de marque partagés.
