"""Visible processing skeleton; no placeholder task reports completed ETL work."""

from datetime import datetime, timezone

from airflow.sdk import DAG, task


@task
def implementation_pending(stage: str) -> None:
    raise NotImplementedError(f"SkyPoints stage '{stage}' is not implemented yet.")


with DAG(
    dag_id="skypoints_ingestion",
    description="SkyPoints ingestion scaffold: processing implementation pending",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    tags=["skypoints", "scaffold"],
) as dag:
    stages = [
        implementation_pending.override(task_id=name)(name)
        for name in [
            "verify_delivery",
            "load_raw",
            "prepare_members",
            "flatten_redemptions",
            "publish_batch",
            "reconcile_counts",
        ]
    ]
    for previous, following in zip(stages, stages[1:]):
        previous >> following
