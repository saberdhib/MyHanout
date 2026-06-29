# 2 · AI Strategy — MyHanout AI

## AI Vision
Faire d'un commerçant de proximité un « commerçant augmenté » : une IA copilote,
explicable et sous contrôle humain, qui anticipe la demande et fluidifie le réassort,
accessible là où il est déjà — sur WhatsApp.

## AI Maturity Assessment (point de départ)
| Dimension | Niveau initial | Cible 12 mois |
|-----------|----------------|---------------|
| Données | Ad hoc (papier) | Structurées, historisées |
| Modèles | Aucun | Forecasting évalué en continu |
| MLOps | Aucun | Boucle fermée réel→erreur→réentraînement |
| Gouvernance | Aucune | Human-in-the-loop + audit |
| Adoption | Nulle | Usage quotidien WhatsApp |

## Prioritized Use Cases (valeur × faisabilité)
1. **OCR factures + structuration** (valeur ↑, faisabilité ↑) — livré.
2. **Forecasting + suggestion de réassort** (valeur ↑↑) — livré (naïf), à enrichir.
3. **Alertes ruptures/péremptions** (valeur ↑) — socle livré.
4. **Q&A métier / agents** (valeur ↑, faisabilité moyenne) — stubs.
5. **RAG documentaire** (valeur moyenne) — infra pgvector prête, non implémenté.

## AI Roadmap (MVP → V2 → V3)
- **MVP (livré)** : OCR réel, forecasting naïf + features, suggestion explicable,
  WhatsApp (boucle), multi-tenant, RBAC, MLOps (MAE/MAPE + réentraînement versionné).
- **V2** : Prophet/LightGBM en production + backtesting ; LLM extraction structurée des
  factures ; RAG factures ; promotions & météo comme régresseurs ; mémoire d'agents.
- **V3** : multi-canal, recommandations proactives, intégrations POS/compta, analytics
  avancés, marketplace fournisseurs.

## Build vs Buy
| Composant | Décision | Raison |
|-----------|----------|--------|
| OCR | **Buy** (Mistral OCR) + fallback | Qualité > coût de build |
| LLM | **Buy** (Claude/Mistral) via ABC | Pas de modèle maison ; portabilité |
| Forecasting | **Build** (naïf) → Buy libs (Prophet/LGBM) | Contrôle + explicabilité |
| Messaging | **Buy** (WhatsApp Business API) | Standard de fait |
| Orchestration agents | **Build léger** | Besoins simples, éviter la sur-ingénierie |
| Vector store | **Buy** (pgvector dans Postgres) | Pas d'infra séparée |

## Model Selection Rationale
- **Claude** (par défaut LLM applicatif) : qualité de raisonnement, structured output,
  bon pour génération marketing / Q&A / extraction. Abstraction `LLMProvider`.
- **Mistral** : OCR (`mistral-ocr-latest`) + alternative LLM ; souveraineté/coût.
- **ML classique** (naïf → Prophet/LGBM) : prévision tabulaire, explicable, peu coûteux,
  adapté aux faibles volumes d'un commerce. Tous derrière `ForecastModel`.
- Principe : **tout provider est abstrait + mockable** ; le défaut local/CI ne nécessite
  aucune clé.

## Risks & Assumptions
| Risque | Impact | Mitigation |
|--------|--------|------------|
| OCR imprécis sur photos | Données fausses | Confiance + validation humaine obligatoire |
| Données initiales pauvres | Prévisions faibles | Modèle naïf robuste + boucle d'apprentissage |
| Dépendance providers | Coût/disponibilité | ABC + fallback mock, multi-provider |
| Fuite inter-commerces | Critique | Garde-fou tenant central + test d'isolation |
| Faible adoption | Échec produit | UX WhatsApp, friction minimale, explicabilité |
- Hypothèses : le commerçant accepte une saisie quotidienne courte ; WhatsApp reste le canal.
