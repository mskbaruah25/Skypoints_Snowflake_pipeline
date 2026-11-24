# Manual Airflow demonstration

## Before the first orchestrated run

Each notebook has a parameter cell immediately after its imports. For a standalone
notebook run, put a specific date in that cell or leave it as None to use today.
The runner refuses notebooks without a parameter cell.

Keep the existing Snowflake tables, service user, role, warehouse, and private key.
Check `.env.local`, the host key directory, and the key's container path. This
deployment does not create, truncate, or drop warehouse tables during startup.

## Run a delivery

1. Start Docker Desktop when ready.
2. Start MinIO and bucket setup with `docker compose up -d --build`.
3. Open http://localhost:19001 with `admin / admin123`.
4. Upload both source feeds to the landing bucket root. Keep only the intended
   delivery there; the processing date does not filter files by upload date.
5. Start Airflow:
   `docker compose --env-file .env --env-file .env.local --profile airflow up -d --build`.
6. Open http://localhost:18080 with `admin / admin`.
7. Open `skypoints_ingestion`, click Trigger, and enter an eight-digit
   `partition_date`, for example `23112026`.
8. Follow `load_raw -> load_staging -> load_gold` and inspect each task's logs.
9. Check the selected partition in Snowflake RAW/STAGING and the country tables in GOLD.

New deliveries are labelled with the date supplied to the DAG. An identical
already-ingested batch is skipped by RAW's fingerprint check. STAGING refreshes the
selected partition; GOLD merges eligible members into the appropriate country
tables. These protections are in the notebooks, rather than a new hashing layer in
Airflow.

## Failure and retry

The first failed task blocks its downstream task. Inspect its log and executed
notebook, correct the cause, and clear/retry that task using the same DAG run.
The preceding successful task does not need to run again.

Each attempt writes a separate executed notebook under:
`/opt/airflow/logs/notebooks/<date>/<run-id-hash>/attempt-<number>/`.
These files are retained in the Airflow logs volume. Source notebooks stay read-only.

For a complete repeat, trigger another run with the same partition date and the
same delivery. A changed set of files produces a different RAW batch fingerprint;
keep delivery contents stable during a run and its retries.

## Finish

Stop orchestration while keeping MinIO available:

~~~sh
docker compose --profile airflow stop airflow-scheduler airflow-dag-processor airflow-api-server airflow-db
~~~

Automatic landing cleanup, real container execution, and warehouse verification
of the orchestrated run remain separate from the small-kernel tests. The manual
DAG needs no ready.json, event handler, or notification receiver.
