# Roadmap — MyHanout AI

> Positionnement : **socle retail générique**, paramétrable par vertical. Phase de
> démo = **alimentation générale / boucherie**, mais l'architecture (providers
> abstraits + modules activables, cf. `docs/retail-platform.md` et
> `docs/configuration.md`) permet d'adapter à d'autres commerces sans refaire le socle.

Légende : ✅ fait · 🟡 partiel · ⏳ planifié

## ✅ Fait
**Socle & sécurité**
- Mono-repo 4 couches, providers abstraits + **mocks keyless** (tourne sans clé).
- **Multi-tenant** : garde-fou central (isolation par commerce), RBAC, audit, RGPD.
- Auth JWT/refresh, onboarding self-service, dark mode, **PWA installable**, responsive mobile.

**Données entrantes (ETL/ELT)**
- Factures : OCR (mock/mistral/pdf), **import email IMAP**, drag&drop, WhatsApp/Telegram, revue humaine, suivi payé.
- **Caisse (POS)** : connecteur mock/http, ingestion idempotente (`external_ref`).
- Import **JSON** + **sync DWH**, **familles produit**, **historique des prix**.

**Intelligence métier**
- Prévisions (naïf ; Prophet/LGBM en option), **réassort explicable** (3 modes d'envoi).
- **Promos anti-gaspillage** : fin de vie → message IA → **affiche générée** → publication RGPD.
- **Finance (pré-compta)** : OPEX/CAPEX (classifieur IA), trésorerie, valorisation stock, marges, alertes.
- **Chaîne du froid** : capteurs mock/http, alertes HACCP explicables.
- **Boucherie** : lot (bête au poids) → décomposition → **rendement + coût/kg + traçabilité**.
- Assistant IA + RAG (pgvector), mémoire/éval agents, **MLOps** (MAE/MAPE + réentraînement versionné).

**Plateforme & genericité**
- **Modules activables par type de commerce** (`/config/modules`, nav dynamique).
- Data platform : `docker-compose.data.yml` (MinIO/Grafana/Adminer), **dbt** (staging→marts), **DAG Airflow**.
- Vitrine (Astro), **CI/CD** complet (lint/type/tests + intégration pg16+pgvector + builds), docs.

## 🟡 En cours / partiel
- **CRUD WhatsApp & plateforme** : stock + fin de journée OK ; à étendre (dépenses
  exceptionnelles, demande, autres entités) — formulaires + commandes texte.
- **Panneau admin sources/IA** : import JSON/email/POS OK ; manque l'UI pour ajouter
  une API/clé, déposer un fichier (→ raw zone → ingestion), choisir les modèles.
- **Vocabulaire viande** : modèle générique (coupes en texte libre) ; à enrichir en
  **alias configurables** (av5, aloyau, bcu…) une fois le lexique métier fourni.
- **Native mobile** : web + PWA aujourd'hui ; app **native (Expo/React Native)** = chantier dédié.

## ⏳ Planifié
1. CRUD WhatsApp/plateforme complet (dépenses exceptionnelles, demande, ajustements).
2. Panneau admin : connecteurs (API/clés) + upload fichiers + sélection modèles IA.
3. **Templates verticaux** prêts (boucherie, primeur, boulangerie, supérette) = modules + libellés + unités.
4. Historique prix avancé (courbes UI, dérive, comparaison fournisseurs).
5. Forecasting prod (Prophet/LGBM activés, détection de drift, registre de modèles).
6. Connecteurs réels (réseaux sociaux, caisses, capteurs LoRaWAN/MQTT).
7. Native app (Expo) : caisse hors-ligne, scan code-barres, sync serveur.
8. Webhooks temps réel capteurs/caisse + scheduling Airflow des relevés.
9. Notifications push (PWA/WhatsApp) sur alertes (rupture, marge, chaîne du froid).
10. Billing (paliers humains, sans coupure brutale) — hors périmètre démo.

Voir aussi : `docs/retail-platform.md`, `docs/configuration.md`, `docs/ai-models.md`,
`docs/data-engineering.md`.
