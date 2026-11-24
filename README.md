# SkyPoints pipeline

Airline loyalty data processing with MinIO, local PySpark, Airflow, and Snowflake.

The RAW, STAGING, and GOLD notebooks hold the processing logic. The manual Airflow
DAG runs them in order with one selected processing date. The orchestration code
and small-kernel tests are in place. The approved notebook configuration changes
have been applied; review [the exact changes](docs/notebook-airflow-changes.md).
A Docker image build and a real orchestrated warehouse run have not been tested
for this change.

## Manual workflow

1. Upload a complete delivery to the root of the MinIO landing bucket:
   `members_*.txt` and `redemptions_*.json`.
2. Open Airflow and trigger `skypoints_ingestion`.
3. Enter `partition_date` as an eight-character string, such as `23112026`.
4. Airflow runs `load_raw -> load_staging -> load_gold`.

RAW labels the incoming records with that date. STAGING reads that date's RAW
partition, and GOLD reads that date's STAGING partition. The date does not select
files by filename or upload time; RAW reads the matching files currently at the
bucket root.

Keep only the intended delivery in landing. Move previous deliveries to a separate
archive location before uploading a new delivery. Automatic landing-file archiving
is still pending.

There is no automatic schedule or file-drop trigger. Only one DAG run and one
notebook task run at a time. A task failure blocks downstream work; use the same
date when retrying the failed task.

## Start services when needed

Docker Desktop must already be running. These commands do not configure its VM
resources.

For MinIO and its one-shot bucket setup only:

~~~sh
docker compose up -d --build
~~~

The default stack starts MinIO and creates the landing bucket. Its setup also
removes the old bucket notification configuration. It does not upload, move, or
delete source objects.

To add Airflow, use the optional `airflow` profile. Load local service settings
from `.env` and private Snowflake overrides from `.env.local`:

~~~sh
docker compose --env-file .env --env-file .env.local --profile airflow up -d --build
~~~

Airflow's profile adds PostgreSQL, the API/UI server, the DAG processor, the
scheduler, and a one-shot metadata setup. These Airflow components share the single
`skypoints-airflow:dev` image. Spark runs only while a notebook task is executing.

To stop Airflow while leaving MinIO running:

~~~sh
docker compose --profile airflow stop airflow-scheduler airflow-dag-processor airflow-api-server airflow-db
~~~

Normal stops retain named-volume data. Avoid `down -v` unless you intend to delete
the named volumes.

## Local access

| Service | Address | Login |
| --- | --- | --- |
| MinIO object browser | http://localhost:19001 | admin / admin123 |
| MinIO S3 API | http://localhost:19000 | Same credentials |
| Airflow UI | http://localhost:18080 | admin / admin |
| PostgreSQL metadata | Internal Compose network only | admin / admin |

Published ports bind to localhost and stay fixed. Container tasks use
`http://minio:9000` for MinIO. Snowflake remains an external cloud service.

Existing PostgreSQL volumes retain the logins created during their first setup.
Changing `AIRFLOW_DB_USERNAME` or `AIRFLOW_DB_PASSWORD` in an environment file
requires updating that login inside the existing database too. The original local
metadata owner was `airflow`; its objects are retained, and the current `admin`
login inherits access to them. The database health check verifies the configured
username and password with a real SQL connection.

## Snowflake configuration

Use the existing service user and key-pair authentication. Supply account, user,
role, warehouse, database, and key passphrase through the private `.env.local`.
The required RAW, STAGING, and GOLD warehouse tables must already exist; the DAG
does not provision or reset them.

`SNOWFLAKE_SECRETS_DIR` selects the host directory mounted read-only into the
scheduler at `/run/secrets`. `SNOWFLAKE_PRIVATE_KEY_FILE` is the corresponding
container path, normally `/run/secrets/snowflake_key.p8`.
`SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE` selects the key for manual Mac notebook runs.
Private overrides and keys are excluded from Git and Docker build contexts.

Only the scheduler and its task processes receive Snowflake credentials. DAG
parsing does not access MinIO, Snowflake, credentials, or notebook contents.

The existing read-only connection check is available with:

~~~sh
skypoints/bin/python -m skypoints.cli check-snowflake
~~~

## Notebook execution and storage

Papermill executes each notebook in a fresh `skypoints` Python kernel from the
isolated Spark environment. The image includes Java 17, PySpark 3.5.7, the notebook
libraries, and the pinned S3/Snowflake connector JARs. Spark uses `local[1]` and a
512 MB driver heap for the local demonstration.

Source notebooks are mounted read-only. Executed copies and errors are saved in
the persistent Airflow logs volume:

~~~text
/opt/airflow/logs/notebooks/<partition_date>/<run-id-hash>/attempt-<number>/<stage>.ipynb
~~~

Different DAG runs and retries have separate output paths. An unprepared notebook
without its parameter cell fails before any cells execute.

MinIO objects persist in `minio-data`, Airflow metadata in `airflow-db-data`, and
logs/results in `airflow-logs`. PostgreSQL holds orchestration metadata; business
records reside in Snowflake RAW, STAGING, and GOLD.

## Local development and checks

Use the existing `skypoints` virtual environment with Python 3.11. Dependencies
are listed in `requirements.txt`. Docker uses `requirements.lock` for Airflow and
`requirements-spark.lock` for the isolated notebook environment.

~~~sh
skypoints/bin/python -m pip install -r requirements.txt
skypoints/bin/python -m ipykernel install --sys-prefix --name skypoints --display-name "SkyPoints (Python 3.11)"
skypoints/bin/python -m pytest -q tests/unit tests/integration/test_notebook_execution.py
docker compose --env-file .env.example --profile airflow config --quiet
~~~

Unit tests cover connection setup and orchestration. Integration tests execute
tiny temporary notebooks with local kernel ports; they do not run Spark, Docker,
or Snowflake. They check date injection, leading zeroes, retry output separation,
source-file preservation, and failure propagation. See [tests](tests/README.md).

The separate generator remains in the sibling `../data-generator/` folder, outside
this Git repository. Its optional container integration is separate from the manual
upload workflow. Legacy Python/SQL scaffold files are not used by the notebook DAG.

See [design](docs/design.md) and [demo instructions](docs/demo.md).
Codex assisted with implementation and review.

References: [Airflow parameters](https://airflow.apache.org/docs/apache-airflow/3.4.0/core-concepts/params.html),
[Papermill parameter cells](https://papermill.readthedocs.io/en/latest/usage-parameterize.html).
