# RGPD & Pricing — MyHanout AI

## Privacy-by-design (RGPD)
- **Consentement explicite** : un client n'est contacté que s'il a `consent_opt_in`
  (horodaté `consent_at`). La diffusion promo exclut systématiquement les non-consentants.
- **Minimisation** : on ne stocke que le nécessaire (contact + consentement). Pas de
  donnée sensible. Les providers externes sont optionnels ; en mock, **rien ne sort**.
- **Isolation stricte** : multi-tenant (garde-fou central) — un commerce n'accède jamais
  aux données d'un autre.
- **Traçabilité** : `audit_log` sur les actions sensibles ; tracing par requête.
- **Contrôle humain** : aucune action sortante (commande, message client) sans validation.
- **Droits** : suppression en cascade (factures/commandes) ; export des données du tenant
  (brique DWH/export à finaliser) → portabilité & droit à l'effacement.
- **Canal léger** : WhatsApp/Telegram suffisent ; pas d'app lourde, pas de collecte tierce.

> Posture « on ne stocke pas chez des tiers » : par défaut, traitement local + mock,
> aucune donnée envoyée à un service externe sans configuration explicite et consentie.

## Pricing humain (dégressif, sans coupure brutale)
Principe : un commerçant en difficulté ne perd jamais son outil du jour au lendemain.

| Palier | Contenu | Note |
|--------|---------|------|
| **Actif** | Toutes les fonctions (IA, promos, WhatsApp, prévisions) | abonnement standard |
| **Grâce (2-3 mois)** | En cas d'impayé : **tout reste actif**, rappels doux | aucune coupure |
| **Rétrogradé** | « Stockage + requêtes de données » à petit prix | garde ses données & l'accès lecture |
| **Réactivation** | Paiement différé possible → retour à Actif | sans perte de données |

- Modélisable sans rien casser (champ d'état d'abonnement sur l'organisation) ; **l'enforcement
  reste non bloquant par design** — on dégrade les fonctionnalités, on ne supprime pas l'accès.
- Billing complet (facturation, paliers tarifaires) = brique ultérieure, hors périmètre démo.
