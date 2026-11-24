"""Manually run the three SkyPoints notebooks for one processing date."""

from datetime import datetime, timedelta, timezone

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param


with DAG(
    dag_id="skypoints_ingestion",
    description="Run RAW, STAGING, and GOLD notebooks for a selected partition date",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(seconds=30),
        "execution_timeout": timedelta(hours=2),
    },
    params={
        "partition_date": Param(
            type="string",
            pattern=r"^[0-9]{8}$",
            title="Partition date (DDMMYYYY)",
            description="For example: 23112026. Use the same date when retrying a delivery.",
            examples=["23112026"],
        ),
    },
    tags=["skypoints", "manual", "notebooks"],
) as dag:
    notebook_tasks = []

    for stage in ("raw", "staging", "gold"):
        notebook_tasks.append(
            BashOperator(
                task_id=f"load_{stage}",
                bash_command=(
                    "exec /opt/spark-venv/bin/python "
                    f"-m skypoints.notebooks --stage {stage}"
                ),
                env={
                    # Pass user input as data, rather than embedding it in shell code.
                    "SKYPOINTS_PARTITION_DATE": "{{ params.partition_date }}",
                    "SKYPOINTS_RUN_ID": "{{ run_id }}",
                    "SKYPOINTS_TASK_ATTEMPT": "{{ ti.try_number }}",
                },
                append_env=True,
                cwd="/opt/airflow",
                do_xcom_push=False,
            )
        )

    notebook_tasks[0] >> notebook_tasks[1] >> notebook_tasks[2]
