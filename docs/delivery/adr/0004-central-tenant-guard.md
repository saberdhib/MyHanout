# ADR 0004 — Garde-fou tenant central (events ORM)

**Statut** : accepté · **Date** : 2026-06

## Contexte
Le multi-tenant est une exigence de **sécurité** : une fuite inter-commerces serait
critique. Un filtre `WHERE organization_id = ?` répété dans chaque requête est fragile
(une requête oubliée = fuite).

## Décision
Garde-fou **central** (`app/core/tenancy.py`) :
- `organization_id` courant dans un **ContextVar**, alimenté **uniquement par le token JWT**.
- Event `do_orm_execute` → `with_loader_criteria(TenantMixin, …)` : filtre **automatique**
  de tous les SELECT ORM (y compris `session.get`, jointures, relations).
- Event `before_flush` : estampille `organization_id` sur les INSERT.

## Conséquences
- ➕ Isolation par défaut, même si un service oublie le filtre. Test d'isolation explicite.
- ➕ Le client ne peut pas falsifier le tenant (vient du token, validé via membership).
- ➖ Les requêtes **SQL brutes hors ORM** échappent au filtre → interdites sur tables tenant
  (documenté). Le contexte doit être posé avant toute requête (fait dans `get_current_user`).
