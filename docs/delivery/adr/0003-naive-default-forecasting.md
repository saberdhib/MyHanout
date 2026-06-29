# ADR 0003 — Modèle de forecasting naïf par défaut

**Statut** : accepté · **Date** : 2026-06

## Contexte
Prophet/LightGBM sont lourds (compilation, taille image, données) et un commerce démarre
avec peu d'historique. Il faut prouver le pipeline bout-en-bout sans dépendance lourde.

## Décision
Implémentation **`NaiveForecastModel` par défaut** : moyenne mobile × saisonnalité hebdo ×
jours fériés × fêtes. Prophet/LGBM sont des implémentations optionnelles
(`pip install ".[forecasting]"`) derrière la même interface `ForecastModel`.

## Conséquences
- ➕ `predict()` fonctionne immédiatement sur les seeds ; images légères ; CI rapide.
- ➕ Modèle **explicable** (chaque suggestion porte sa décomposition).
- ➕ Boucle MLOps (MAE/MAPE + réentraînement versionné) agnostique du modèle.
- ➖ Précision limitée sur signaux complexes → V2 active Prophet/LGBM + météo/promos.
