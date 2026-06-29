# Gouvernance — RBAC, audit, human-in-the-loop, RGPD

MyHanout AI agit sur des données commerciales sensibles et peut proposer des
actions (commandes). La gouvernance garantit **contrôle humain, traçabilité et
conformité**.

## RBAC (contrôle d'accès)

- Modèle : `User` ↔ `Role`. `role.permissions` = liste de scopes (`*` = tous).
- Rôles par défaut (seed) : `owner` (`*`), `manager` (stocks/orders/invoices/forecasts),
  `staff` (stocks/invoices), `viewer` (read).
- Application : dépendance `require_permission(scope)` sur chaque endpoint.

| Rôle    | Stocks | Factures | Prévisions | Commandes (valider) |
|---------|:------:|:--------:|:----------:|:-------------------:|
| owner   |   ✅   |    ✅    |     ✅     |         ✅          |
| manager |   ✅   |    ✅    |     ✅     |         ✅          |
| staff   |   ✅   |    ✅    |     —      |         —           |
| viewer  |   👁️   |    👁️    |     👁️     |         —           |

## Human-in-the-loop

Les actions **sensibles** ne sont jamais exécutées automatiquement :

- Un agent (ex. `agent_order`) **propose** une action (`AgentAction.requires_approval = True`).
- L'`agent_governance` vérifie l'action (type sensible, plafonds, droits).
- L'humain valide via `POST /orders/{id}/approve` (statut `pending_approval` → `approved`).
- La validation est **tracée** dans `audit_log`.

## Audit

- **Middleware** (`core/audit.py`) : journalise toutes les requêtes mutantes
  (méthode, chemin, statut, durée) et alimente les métriques Prometheus.
- **Table `audit_log`** : actions sensibles explicites (`order.approve`, ...) avec
  `user_id`, `resource`, `resource_id`, `detail`, horodatage.

## RGPD / conformité

- **Minimisation** : ne stocker que les données nécessaires (produits, ventes,
  factures, fournisseurs).
- **Secrets** : exclusivement via variables d'environnement (`.env`, jamais versionné).
- **Traçabilité** : journal d'audit pour les accès/actions sensibles.
- **Droit à l'effacement** : suppression en cascade (`invoice_line`, `order_line`)
  ; procédure d'export/suppression par commerçant à implémenter.
- **Explicabilité** : chaque décision IA porte une `explanation` consultable.

> Statut : socle en place (RBAC, audit, human-in-the-loop). À compléter :
> authentification par token, chiffrement au repos, politique de rétention.
