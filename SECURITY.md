# Politique de sécurité

## Signaler une vulnérabilité

Merci de **ne pas** ouvrir d'issue publique pour une faille de sécurité.
Contactez-nous en privé : **security@myhanout.ai** (ou via un message privé au
mainteneur). Nous accusons réception sous quelques jours ouvrés et tenons informé
du correctif.

Merci d'inclure : description, étapes de reproduction, impact estimé, et si
possible une suggestion de correctif.

## Périmètre

Ce dépôt est une **base produit** (démo fonctionnelle). Points d'attention :

- **Aucun secret dans le dépôt.** Toute configuration sensible passe par `.env`
  (non suivi). `.env.example` ne contient que des **placeholders**.
- **Mock-first / keyless** : par défaut, aucune intégration externe n'est appelée.
  Les vrais providers (LLM, OCR, WhatsApp, capteurs, caisse…) ne s'activent que si
  vous fournissez vos propres clés.
- **Données fictives** : `data/seeds/` et les fixtures de test ne contiennent que
  des données inventées (aucune donnée personnelle réelle).
- **Multi-tenant** : l'isolation par commerce est une exigence de sécurité
  (garde-fou central). Un bug d'isolation = vulnérabilité — à signaler en priorité.

## Bonnes pratiques pour les déploiements

- Changez `SECRET_KEY` et les mots de passe par défaut avant toute mise en ligne.
- Stockez les secrets dans un gestionnaire dédié (SSM / Secret Manager), jamais en repo.
- Restreignez l'accès réseau à PostgreSQL/Redis ; activez HTTPS devant l'API.
- Les clés API doivent être à privilèges minimaux et rotables.

## Versions supportées

Projet en évolution rapide : seule la branche `main` est maintenue.
