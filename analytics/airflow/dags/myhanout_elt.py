"""DAG ELT quotidien MyHanout (exemple, exécutable sur Airflow 2.x).

Pipeline : extrait un snapshot OLTP → dépose en raw zone (MinIO/S3) → dbt build
→ dbt test → rafraîchit Grafana. Idempotent (rejouable par date `ds`).

En local, Airflow est optionnel : sans lui, les mêmes étapes tournent via cron/make.
Aucun secret en dur : tout vient des Variables/Connections Airflow ou de l'environnement.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "myhanout",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="myhanout_elt",
    description="ELT quotidien : OLTP -> raw (MinIO) -> dbt -> Grafana",
    schedule="0 3 * * *",  # tous les jours à 03:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["myhanout", "elt"],
) as dag:
    # 1) Snapshot OLTP -> fichier (réutilise l'endpoint DWH ou un dump SQL).
    extract_oltp_snapshot = BashOperator(
        task_id="extract_oltp_snapshot",
        bash_command='echo "EL: snapshot OLTP du {{ ds }} (brancher /import/dwh/sync ou pg_dump)"',
    )

    # 2) Dépose le snapshot dans la raw zone S3-compatible (MinIO en local).
    load_raw_minio = BashOperator(
        task_id="load_raw_minio",
        bash_command='echo "EL: upload raw -> s3://myhanout-raw/snapshots/{{ ds }}/"',
    )

    # 3) Transformations analytiques versionnées.
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd ${DBT_PROJECT_DIR:-/opt/airflow/analytics/dbt} && dbt build",
    )

    # 4) Qualité des données (tests dbt).
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd ${DBT_PROJECT_DIR:-/opt/airflow/analytics/dbt} && dbt test",
    )

    # 5) Rafraîchit les dashboards (no-op si Grafana lit le pg en direct).
    refresh_grafana = BashOperator(
        task_id="refresh_grafana",
        bash_command='echo "Dashboards Grafana à jour (datasource pg provisionnée)"',
    )

    extract_oltp_snapshot >> load_raw_minio >> dbt_build >> dbt_test >> refresh_grafana
