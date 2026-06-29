# Roadmap — MyHanout AI

## ✅ Phase 0 — Scaffold (livré)

Mono-repo déployable, structure en 4 couches, interfaces abstraites + mocks,
pipeline bout-en-bout fonctionnel sur données de seed.

- [x] Structure, configs qualité (ruff/black/mypy/pytest/pre-commit), docker-compose
- [x] Modèle de données + migration Alembic + seeds
- [x] Ingestion/OCR (abstraction + mock + parsing + validation)
- [x] Forecasting (modèle naïf fonctionnel + features + stubs Prophet/LGBM)
- [x] Agents (6) + orchestration LLM (abstraction + mock)
- [x] API lecture + webhook WhatsApp (echo + routing) + audit/RBAC
- [x] Dashboard frontend
- [x] CI/CD + documentation

## 🚧 Phase 1 — MVP exploitable

- [ ] Authentification réelle (JWT, login/refresh) + gestion des utilisateurs
- [ ] OCR Mistral réel + extraction structurée des factures (LLM function calling)
- [ ] Persistance des factures ingérées (pipeline → DB) + rapprochement SKU
- [ ] Endpoints d'écriture (CRUD produits/stocks/fournisseurs)
- [ ] Génération automatique d'alertes (rupture/péremption/échéance) via workers
- [ ] Envoi WhatsApp réel (Business API) pour les notifications

## ✅ Phase 1 & 2 — Chaîne de valeur réelle (livré)

**Phase 1** — OCR Mistral réel (PDF+image, fallback), persistance des factures
avec validation humaine (upload→review→approve/reject, idempotence), auth JWT/RBAC,
migrations validées sur pg16+pgvector.

**Phase 2** — Boucle quotidienne fermée :
- [x] WhatsApp Business réel (webhook signé, texte+image→OCR, machine à états)
- [x] Saisie de fin de journée (WhatsApp + dashboard, idempotente, auditée)
- [x] Suggestion de commande explicable à la demande (réutilise le forecasting)
- [x] Action de commande 3 modes (whatsapp_auto / draft / record_only), human-in-the-loop
- [x] Dashboard live (stock/prévisions/suggestions/écarts, polling)
- [x] Boucle MLOps : écart prévu/réel → MAE/MAPE → réentraînement versionné

## 🔮 Phase 3 — Intelligence avancée

- [ ] Forecasting Prophet/LightGBM en production + backtesting/évaluation
- [ ] Fêtes/saisonnalité paramétrables par commerçant (config en base)
- [ ] RAG documentaire (pgvector) : Q&A sur l'historique de factures
- [ ] Actions WhatsApp transactionnelles (passer commande) avec validation
- [ ] Recommandations de réassort automatiques (agent_order proactif)

## 🌐 Phase 3 — Scale & produit

- [ ] Multi-tenant (plusieurs commerces) + isolation des données
- [ ] Tableau de bord analytics (marges, top produits, cashflow)
- [ ] Exports comptables, intégrations tierces
- [ ] Application mobile / PWA
