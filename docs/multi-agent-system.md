# Le système multi-agents MyHanout — adapté au commerce alimentaire de proximité

> Inspiration : les « multi-agent AI systems » de la planification retail (type RELEX),
> mais **dégraissés** et **recentrés** sur un seul métier : le commerçant alimentaire de
> proximité (boucherie, épicerie, primeur, boulangerie, supérette, traiteur).
> Principe directeur inchangé : **human-in-command · explicable · auditable · RGPD · mock-first.**

## 1. L'idée en une phrase
MyHanout n'est pas « un logiciel », c'est une **équipe d'agents IA spécialisés** qui
travaillent votre commerce en continu, se coordonnent, et vous préparent **chaque matin un
briefing d'actions prêtes à valider** — vous décidez, ils exécutent (commande, démarque,
promo, message client). Pas de boîte noire : chaque proposition porte son **pourquoi**.

## 2. Pourquoi « multi-agents » et pas « une grosse IA »
- **Spécialisation** : un agent = un domaine maîtrisé (stock, prix, frais…), plus fiable
  qu'un modèle généraliste.
- **Explicabilité** : chaque agent justifie sa reco → confiance du commerçant.
- **Sécurité** : un agent **Gouvernance** filtre toute action sortante (human-in-the-loop).
- **Extensibilité** : ajouter une capacité = ajouter un agent derrière le même contrat
  (`BaseAgent`), sans toucher au reste.

## 3. Ce qui existe déjà (socle)
`intelligence/agents/` : contrat `BaseAgent` (intents, `run()`, `AgentResult` avec
`explanation` + `actions` + `confidence`), **orchestrateur** (détection d'intent → routage →
revue gouvernance), **mémoire** (`agent_memory`, tenant) et **évaluation** (golden set).
Agents actuels : **Réassort** (order), **Stock**, **Finance**, **Marketing/Promo**,
**Support** (fallback conversationnel), **Gouvernance** (garde-fou).

## 4. L'équipe d'agents cible (proximité alimentaire)

### Agents « pilotage » (déjà là, à enrichir)
| Agent | Rôle | Capacités RELEX couvertes |
|---|---|---|
| **Demande** 🔮 | prévoit les ventes (jour/produit), détecte les pics, intègre signaux externes (météo, vacances, paie, match) & métier | Planification & détection de la demande, saisonnalité |
| **Réassort** 🛒 | quoi/combien/quand commander, par fournisseur, avec délais | Réappro & allocation, commandes frais |
| **Stock** 📦 | ruptures, surstock, DLC/péremption, inventaire frais | Inventaire bout-en-bout, inventaire frais |
| **Finance** 💶 | factures (OCR), trésorerie, marges, OPEX/CAPEX | Diagnostic coûts |
| **Marketing/Promo** 📣 | promos explicables + affiches IA + communication multi-canal | Planification des promotions |
| **Gouvernance** 🛡️ | valide/bloque les actions sortantes, audit | (transverse : human-in-command) |
| **Support** 💬 | assistant conversationnel WhatsApp/Slack/web | (interface) |

### Nouveaux agents (les trous identifiés — par priorité)
| Agent | Rôle | Capacité comblée | Prio |
|---|---|---|---|
| **Démarque** 🏷️ | optimise la démarque du frais : « lot périme dans 2 j → -30 % maintenant pour récupérer 70 % de marge plutôt que 100 % de perte » | Démarques produits frais (markdown) | ⭐ 1 |
| **Production** 🥖 | combien préparer/cuire/découper aujourd'hui (recettes/nomenclature → conso matière & coût) | Production en magasin + recettes frais | ⭐ 2 |
| **Tâches du jour** ✅ | consolide toutes les recos (réassort, démarque, promo, froid) en **une checklist d'actions** cochable = le « briefing du matin » | Exécution magasin | ⭐ 3 |
| **Effectifs** 🧑‍🍳 | dérive du forecast un besoin de personnel (« samedi +40 % → +1 personne ») | Prévision de la charge de travail | 4 |
| **Prix** 🎯 | suggère un prix cohérent (marge cible, historique, élasticité légère) | Optimisation des prix | 5 |
| **Chaîne du froid** ❄️ | surveille températures, conformité HACCP, alerte | Diagnostic / qualité frais | (a un service, à « agentifier ») |
| **Qualité/Conformité** 🧾 | écarts, traçabilité, DLC, HACCP | Diagnostics | (modules `quality`/`meat` existants) |

## 5. Orchestration : du chat réactif au cycle proactif
Aujourd'hui l'orchestrateur est **réactif** (un message → un agent). On ajoute un mode
**proactif** : un **cycle quotidien** (déjà industrialisable via `PipelineRun`/Celery) où
chaque agent produit ses recommandations du jour → l'agent **Tâches du jour** les
**consolide et priorise** → un **Briefing du matin** part sur WhatsApp/Slack.

```
                 ┌─────────────── Cycle quotidien (PipelineRun) ───────────────┐
  Données  ─────▶│  Demande → Réassort → Stock → Démarque → Production → Prix    │
 (POS, OCR,      │        \________________  consolidation  ________________/    │
  capteurs,      │                         ▼                                     │
  signaux)       │                 Agent « Tâches du jour »                      │
                 │                         ▼                                     │
                 │        Briefing du matin (priorisé, explicable)               │
                 └───────────────────────────┬─────────────────────────────────┘
                                              ▼
                         Gouvernance (human-in-command)
                                              ▼
                    Le commerçant valide → exécution (commande, démarque, promo)
```

Toute action garde `requires_approval` par défaut ; la **Gouvernance** ne laisse passer en
auto que des actions whitelistées à faible risque. Chaque étape est **tracée** (audit) et
**explicable** (`explanation`).

## 6. Principes non négociables (rappel)
- **Human-in-command** : l'IA propose, l'humain dispose. Aucune commande/message/publication
  sans validation (sauf whitelist gouvernance).
- **Explicabilité** : chaque reco porte sa raison + sa confiance.
- **Mock-first / keyless** : chaque agent tourne sans clé (LLM mock par défaut).
- **Multi-tenant** : tout passe par le garde-fou d'isolation ; mémoire agent tenant.
- **Spécifique client = `.env` + données tenant**, jamais en dur dans `backend/app/`.

## 7. Feuille de route d'implémentation
1. **Agent Démarque** (⭐) — ✅ **fait** : modèle `markdown_suggestion` + moteur pur
   (`intelligence/markdown/engine.py` : cash récupéré vs perte selon DLC & écoulement) +
   agent (`agent_markdown`) + endpoints (`/markdown`, `/scan`, `/apply|reject`) + page
   `Markdown.tsx` + tests (`test_markdown.py`). Module `markdown`.
2. **Agent Production + Recettes** (⭐) — ✅ **fait** : nomenclature (`recipe`/`recipe_item`),
   moteur pur (`intelligence/production/engine.py` : besoin net arrondi au rendement),
   `recipe_service` + `production_service` (plan + besoins ingrédients agrégés/coût), agent
   `agent_production`, endpoints `/recipes` & `/production/*`, page `Production.tsx`, tests
   (`test_production.py`). Module `production`.
3. **Agent Tâches du jour** — ✅ **fait** : `services/briefing_service.py` consolide
   alertes + réassort + démarque + production en tâches priorisées (`daily_briefing`/
   `briefing_item`), agent `agent_briefing`, endpoints `/briefing/*`, page `Briefing.tsx`,
   **câblé dans le cycle quotidien** (job `daily` → asset briefing), envoi WhatsApp/Slack.
   Tests `test_briefing.py`. Module `briefing`.
4. **Effectifs** + **Prix** — ✅ **fait** : moteurs purs (`intelligence/staffing/engine.py`,
   `intelligence/pricing/engine.py`), services (`staffing_service` : affluence prévue par
   jour de semaine → renfort ; `pricing_service` : marge cible + arrondi psychologique),
   agents `agent_staffing`/`agent_pricing`, endpoints `/staffing/plan` & `/pricing/*`,
   pages `Staffing.tsx`/`Pricing.tsx`. Modules `staffing`/`pricing`.
5. **Agentification Froid/Qualité** + **Diagnostic** : ensuite.
5. **Vitrine** : reformuler le positionnement « votre équipe d'agents IA » (page dédiée).

> Chaque brique suit le même patron : ABC/contrat → impl mock keyless → service → endpoint →
> front → tests (sqlite + mocks). Gate vert à chaque commit.
