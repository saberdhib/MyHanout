# ADR 0005 — Human-in-the-loop sur les actions sortantes

**Statut** : accepté · **Date** : 2026-06

## Contexte
L'IA propose des achats et peut contacter des fournisseurs. Une action automatique erronée
a un coût réel (commande inutile, relation fournisseur). Confiance = contrôle laissé à l'humain.

## Décision
Toute action **sensible/sortante** exige une **validation humaine explicite** :
- Commandes : statut `pending_review`/`suggested` → `confirmed` par un humain ; jamais d'envoi
  sans confirmation ; `agent_governance` contrôle les actions des agents.
- Factures : OCR → `pending_review` → `approve/reject` humain avant écriture des lignes.
- Tout est **tracé** (`audit_log`) et **explicable** (`explanation`/`reasons`).

## Conséquences
- ➕ Confiance, conformité, auditabilité ; aligné RGPD/Responsible AI.
- ➕ Différenciateur produit (le commerçant garde la main).
- ➖ Friction d'un clic de validation — assumée et minimisée (UX WhatsApp/dashboard).
