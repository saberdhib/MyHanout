# MyHanout AI — Enterprise Delivery

Dossier de livraison « enterprise » : discovery, stratégie, architecture, données, ADRs,
et la matrice de couverture de la checklist de delivery.

## Documents
- [01 · Business Discovery](01-business-discovery.md) — brief, personas, journeys, BRD, KPIs, ROI
- [02 · AI Strategy](02-ai-strategy.md) — vision, maturité, use cases, roadmap, build-vs-buy, modèles, risques
- [03 · Solution Architecture](03-solution-architecture.md) — C4, data flow, séquences, agents, déploiement
- [04 · Data Architecture](04-data-architecture.md) — sources, intégrations, schéma, data dictionary, ETL, qualité, feature store
- [ADRs](adr/README.md) — décisions structurantes

Docs techniques existantes : [`../architecture.md`](../architecture.md) ·
[`../data-model.md`](../data-model.md) · [`../api-design.md`](../api-design.md) ·
[`../governance.md`](../governance.md) · [`../multitenancy.md`](../multitenancy.md) ·
[`../roadmap.md`](../roadmap.md)

## Couverture de la checklist (RetailOS / MyHanout AI)
Légende : ✅ fait · 🟡 partiel · ⬜ à faire.

| # | Section | État | Où |
|---|---------|------|----|
| 1 | Business Discovery | ✅ | delivery/01 |
| 2 | AI Strategy | ✅ | delivery/02 |
| 3 | Solution Architecture | ✅ | delivery/03 (C4, séquences, agents, déploiement) |
| 4 | Data Architecture | ✅ | delivery/04 + data-model.md |
| 5 | OCR Pipeline | ✅ | Phase 1 (upload, OCR, validation, human, confidence, errors) — 🟡 LLM extraction |
| 6 | Forecasting | 🟡 | naïf + features + MAE/MAPE + API/dashboard ; ⬜ Prophet/LGBM, météo |
| 7 | AI Agents | 🟡 | 6 agents + supervisor + tool-calling minimal ; ⬜ mémoire, eval |
| 8 | LLM Platform | 🟡 | Claude/Mistral, structured output, conversation history ; ⬜ prompt lib/versioning, RAG, guardrails |
| 9 | APIs | ✅ | FastAPI, OpenAPI/Swagger, auth, logging, versioning ; ⬜ rate limiting |
| 10 | Frontend | 🟡 | dashboard/KPI/forecast/inventory, responsive, branding ; ⬜ dark mode, tablet |
| 11 | WhatsApp | 🟡 | webhook signé, commandes, notifs, order validation ; ⬜ voice |
| 12 | Infrastructure | 🟡 | Docker, compose, CI/CD, secrets env ; ⬜ Terraform, cloud |
| 13 | Monitoring | 🟡 | logs, metrics, health, MLOps ; ⬜ tracing, cost/model/agent monitoring |
| 14 | Security | ✅ | auth, RBAC, audit, secrets, **isolation tenant** ; 🟡 GDPR, ⬜ encryption at-rest |
| 15 | Governance | ✅ | human-in-the-loop, audit, governance.md ; ⬜ risk register formel, operating model |
| 16 | Testing | 🟡 | unit + integration (pg) + API ; ⬜ E2E, agent/LLM eval |
| 17 | Documentation | ✅ | README + architecture + api + governance + multitenancy + delivery + **ADRs** ; ⬜ deployment/user/admin guides |
| 18 | Demo Assets | 🟡 | sample dataset (seeds) ; ⬜ vidéo, screenshots, GIFs, slides |
| 19 | Business Deliverables | ⬜ | exec deck, proposal, project plan, adoption |
| 20 | Portfolio | 🟡 | repo GitHub ; ⬜ article, site, blog, PDF archi |

> Détails par phase et PRs : Phase 1 (#1), Phase 2 (#2), Phase 1.5 (#3) — branches non
> mergées en attente de relecture.
