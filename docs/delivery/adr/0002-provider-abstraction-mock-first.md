# ADR 0002 — Providers externes abstraits + mock par défaut

**Statut** : accepté · **Date** : 2026-06

## Contexte
OCR, LLM, WhatsApp, modèles de forecasting sont des dépendances externes coûteuses et
parfois indisponibles. Il faut pouvoir développer/tester sans clé et changer de fournisseur.

## Décision
Chaque dépendance derrière une **interface abstraite** (`OCRProvider`, `LLMProvider`,
`WhatsAppClient`, `ForecastModel`) avec une **implémentation mock par défaut**. La sélection
se fait par variable d'environnement ; sans clé, fabrique → mock (fallback explicite).

## Conséquences
- ➕ Défaut local/CI 100 % mock, sans secret ; tests déterministes (clients HTTP mockés).
- ➕ Portabilité (Claude ↔ Mistral, business ↔ mock) sans toucher la logique métier.
- ➕ Erreurs typées (ex. `OCRQuotaError`) → fallback résilient.
- ➖ Surface d'abstraction à maintenir ; risque de divergence mock/réel (mitigé par tests).
