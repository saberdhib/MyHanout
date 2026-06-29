# analytics/ — couche analytique (dbt · Airflow · Grafana)

Briques **analytiques**, séparées de l'app transactionnelle. Voir
[`docs/data-engineering.md`](../docs/data-engineering.md) pour le tableau complet.

```
analytics/
  dbt/        transformations SQL versionnées (staging -> marts) + tests qualité
  airflow/    DAG d'orchestration ELT (exemple, Airflow 2.x)
  grafana/    datasource provisionnée (Postgres) + (dashboards à venir)
```

## Démarrage rapide
```bash
# Stack data (MinIO + Grafana + Adminer)
docker compose -f docker-compose.data.yml up -d

# dbt (transformations)
cd analytics/dbt
cp profiles.example.yml ~/.dbt/profiles.yml   # adapte l'hôte pg
dbt deps && dbt build                          # build + tests
```

## Cœur vs mouvant (par client)
- **Cœur (versionné)** : les modèles dbt (`models/`), le DAG, la datasource Grafana.
- **Mouvant (par client / déploiement)** : `~/.dbt/profiles.yml` (connexion entrepôt),
  identifiants MinIO/Grafana, buckets, planification Airflow. Voir
  [`docs/configuration.md`](../docs/configuration.md).
