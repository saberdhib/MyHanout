# ml-service — service de forecasting isolé

Frontière de service pour le forecasting (Brique 2). Permet de **scaler le ML
indépendamment** de l'API et du front. **Keyless** : démarre sans aucune clé.

## Lancer

```bash
# Via docker-compose (recommandé) :
docker compose up -d ml-service

# Ou en local :
cd ml-service && pip install -r requirements.txt
uvicorn app:app --port 8001
```

## Endpoints

| Méthode | Route | Rôle |
|---------|-------|------|
| GET  | `/health` | Liveness + version de modèle |
| GET  | `/model/version` | Version du modèle servie (traçabilité MLOps) |
| POST | `/train` | Entraînement (stub versionné) |
| POST | `/predict` | Prévision à partir d'un historique `[{ds, y}]` |

## Intégration backend

L'API principale appelle ce service via `ForecastServiceClient` (mode `http`,
variable `FORECAST_SERVICE_CLIENT=http` + `ML_SERVICE_URL`). **Si le service est
indisponible, l'API retombe automatiquement sur le forecast in-process** : aucune
rupture de service. Par défaut (`inprocess`), ce service n'est pas requis.
