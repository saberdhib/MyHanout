# 1 · Business Discovery — MyHanout AI

## Executive Brief
MyHanout AI est un copilot IA, opéré via **WhatsApp**, pour les commerces de proximité
(bouchers, boulangers, épiceries, artisans). Il transforme un passif documentaire
désordonné (factures papier/PDF) en décisions d'achat fiables : prévision de la demande,
suggestions de réassort explicables, alertes ruptures/péremptions — toujours sous
**contrôle humain**. Objectif : réduire les ruptures et le gaspillage, et rendre 1–3 h/semaine
au commerçant.

## Problem Statement
Le commerçant de proximité gère ses stocks « de tête ». Conséquences : ruptures sur les
produits qui tournent, surstock périssable jeté, trésorerie immobilisée, factures
fournisseurs non suivies. Les outils ERP/POS existants sont trop lourds, chers et non
adaptés à une interface mobile/conversationnelle.

## Business Context
- Marché : commerces indépendants (Maghreb/France en cible initiale).
- Canal d'usage : WhatsApp (déjà adopté, zéro friction d'installation).
- Contrainte clé : faible disponibilité et faible appétence pour les UI complexes.

## Stakeholder Map
| Partie prenante | Intérêt | Implication produit |
|-----------------|---------|---------------------|
| Propriétaire (owner) | Marge, trésorerie, temps | Décideur, valide les commandes |
| Employé (staff) | Saisie rapide, alertes | Saisie fin de journée, exécution |
| Comptable (accountant) | Factures, échéances | Multi-commerces, lecture finance |
| Fournisseur | Commandes claires | Destinataire des bons de commande |
| Éditeur (nous) | Adoption, rétention | Roadmap, gouvernance IA |

## Personas
- **Karim, boucher (owner, 42 ans)** : veut éviter les ruptures le week-end, déteste les
  tableurs, vit sur WhatsApp. Succès = « le bot me dit quoi commander, je valide ».
- **Salma, comptable externe (accountant, gère 8 commerces)** : veut centraliser les
  factures et échéances, sans accès aux commandes fournisseurs.
- **Yassine, employé (staff)** : saisit le stock le soir, reçoit les alertes.

## User Journey (cible)
1. Onboarding self-service (créer commerce, produits, inviter comptable).
2. Import des factures (photo WhatsApp → OCR → validation humaine).
3. Saisie de fin de journée (stock restant + commandes) via WhatsApp/dashboard.
4. Suggestion de commande explicable à la demande → ajustement → validation.
5. Transmission au fournisseur (WhatsApp auto / brouillon / enregistrement).
6. Boucle d'apprentissage : écart prévu/réel → amélioration du modèle.

## Pain Points → Réponse produit
| Pain | Réponse |
|------|---------|
| Ruptures imprévues | Forecasting + suggestion de réassort |
| Gaspillage périssable | Alertes péremption + tampon calibré |
| Factures non suivies | OCR + échéances + rôle comptable |
| Outils trop complexes | WhatsApp + dashboard minimaliste |
| Perte de contrôle | Human-in-the-loop systématique |

## Current vs Future Workflow
- **Actuel** : observation visuelle → commande « au feeling » → facture papier rangée → oubli des échéances.
- **Futur** : données structurées → prévision → suggestion explicable → validation 1-clic → audit complet.

## Business Requirements Document (BRD)
### Functional Requirements
1. Importer et structurer les factures (OCR + validation humaine).
2. Prévoir la demande par produit (saisonnalité, fêtes).
3. Proposer des commandes explicables et ajustables.
4. Transmettre les commandes (3 modes) après validation.
5. Saisir la réalité quotidienne (stock/commandes).
6. Isolation multi-commerces ; rôles (owner/staff/accountant/read_only).
7. Onboarding self-service + invitations.

### Non-Functional Requirements
- **Sécurité** : isolation tenant stricte, RBAC, audit, secrets hors code.
- **Explicabilité** : toute suggestion porte son « pourquoi ».
- **Disponibilité** : healthchecks, dégradation gracieuse (fallback mock/OCR).
- **Coût** : providers externes optionnels ; défaut local 100 % mock.
- **Performance** : API async ; suggestions < 2 s sur catalogue PME.
- **Conformité** : RGPD (minimisation, traçabilité, droit à l'effacement).

## KPIs & Success Metrics
| KPI | Cible 90 j |
|-----|-----------|
| Réduction des ruptures | −30 % |
| Réduction du gaspillage périssable | −20 % |
| Taux d'adoption des suggestions | > 50 % |
| MAPE prévision (produits A) | < 25 % |
| Temps gagné / semaine | 1–3 h |
| Factures traitées via OCR | > 80 % |

## ROI estimation (commerce type)
- Hypothèses : CA mensuel 30 000 €, marge 25 %, pertes (ruptures+gaspillage) ≈ 6 % du CA.
- Gain visé : réduire ces pertes de moitié → ≈ **900 €/mois** récupérés.
- Coût cible SaaS : < 50 €/mois → **ROI > 15×**, payback < 1 mois.
> Estimation indicative à valider par cohorte pilote.
