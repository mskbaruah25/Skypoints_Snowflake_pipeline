# SkyPoints pipeline

Initial project scaffold for the Incubyte data-engineering assessment.

**Status:** the folder layout, single multi-target Dockerfile, Compose definitions,
dependency specifications, and local bootstrap utilities are present. ETL logic,
warehouse DDL/publication SQL, the notification bridge, and the separate generator
are implementation placeholders. The pipeline is not yet an end-to-end demo.
Placeholder entry points fail explicitly rather than reporting successful work.
Snowflake key-pair authentication and a read-only connection check are implemented.

## Architecture

```text
MinIO -> notification handler -> Airflow -> local-mode PySpark -> Snowflake
```

- MinIO retains the original member and redemption files.
- Airflow orchestrates the processing and exposes task status and logs.
- PySpark prepares raw/staging records and derived values.
- Snowflake stores RAW, STAGING, CORE, MART, and OPS business-data tables.
- PostgreSQL stores Airflow metadata only.

## Layout

```text
skypoints-pipeline/
├── Dockerfile                 # Targets: minio, airflow, event-handler, data-generator
├── compose.yaml
├── .env.example
├── .dockerignore
├── .gitignore
├── pyproject.toml
├── requirements.txt           # Local Python development and notebook dependencies
├── requirements*.lock
├── dags/                      # Thin Airflow definitions
├── src/skypoints/              # Processing package and application entry points
├── sql/                       # Warehouse DDL and transactional publication SQL
├── scripts/                   # Container bootstrap, dependency download, demo upload
├── tests/                     # Unit, integration, end-to-end, and fixture locations
├── docs/                      # Design, source contract, demonstration plan
└── secrets/                   # Local keys; only its README is tracked
```

The sibling `../data-generator/` is deliberately outside this Git repository.
Its scaffold is separate; its source and seed data are not committed here.
The assignment PDF, supplied CSVs, downloaded datasets, and notebooks remain in
the parent workspace.

## Local Python development

Use Python 3.11; `.python-version` pins the local interpreter to 3.11.18. The local
virtual environment is named `skypoints` and is separate from the Python package
under `src/skypoints`. Both the environment and project-local interpreter are
excluded from Git and Docker build contexts.

With Python 3.11 installed, create and install the environment with:

```sh
python3.11 -m venv skypoints
source skypoints/bin/activate
python -m pip install -r requirements.txt
python -m ipykernel install --sys-prefix --name skypoints --display-name "SkyPoints (Python 3.11)"
```

In this workspace, the interpreter is also available at
`.python/python/bin/python3.11`. The environment has a notebook kernel named
`skypoints`, displayed as `SkyPoints (Python 3.11)`. Select it or the environment's
`skypoints/bin/python` interpreter when opening a stage notebook.

`requirements.txt` covers local orchestration, Spark processing, storage access,
the notification receiver, notebooks, and tests. Docker continues to use its
service-specific `requirements*.lock` files. Running Spark locally also requires
Java; the Docker image already includes Java 17.

Verified on 2026-11-22: dependency consistency (`pip check`), package imports, the
named notebook kernel, and a small local Spark 3.5.7 DataFrame job using Java 17.

## Snowflake connection

The connection helper reads `.env`, then the private `.env.local`, with process
environment variables taking precedence. Files and credentials are read when the
helper is called, not during module or DAG import.

Set the account, service user, role, warehouse, database, and private-key passphrase
in `.env.local`. For local Python, `SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE` selects the key
on the Mac. Docker uses `SNOWFLAKE_PRIVATE_KEY_FILE`, normally
`/run/secrets/snowflake_key.p8`, inside the scheduler container.

With the `skypoints` environment activated, run:

```sh
python -m skypoints.cli check-snowflake
```

To enter the passphrase privately for a single local check, use:

```sh
python -m skypoints.cli check-snowflake --prompt
```

The command verifies the connected user, role, warehouse, database, current schema,
and visibility of RAW/STAGING/GOLD. It prints no key or passphrase and performs no
data loading or table creation. On 2026-11-23, this check successfully connected as
`SKYPOINTS_PIPELINE` with `SKYPOINTS_PIPELINE_ROLE` and verified all three schemas.
Six unit tests cover configuration precedence and private-key handling.

## Setup and intended startup

Requirements: Docker with Compose 2.17+ and BuildKit. A Snowflake account and key
are needed for warehouse tasks, not for starting the local services.

1. The tracked `.env` contains generated local demo credentials and Snowflake
   placeholders. For real Snowflake settings, copy it to the ignored `.env.local`,
   update that file, and select it with `docker compose --env-file .env.local ...`.
2. When configuring Snowflake, put the key in `SNOWFLAKE_SECRETS_DIR`, normally
   `secrets/snowflake_key.p8` on the host. The directory is mounted read-only at
   `/run/secrets` in the scheduler; `SNOWFLAKE_PRIVATE_KEY_FILE` is the container
   path, normally `/run/secrets/snowflake_key.p8`.
3. Set `DATA_GENERATOR_DIR` if you later use the optional sibling generator.
4. Complete the implementation items listed below before attempting a full demo.

Start the local infrastructure with:

```sh
docker compose up --build -d
```

For subsequent starts, `docker compose up -d` reuses the existing images. The
`airflow-init` service owns the shared Airflow image build; the API, scheduler,
DAG processor, and MinIO setup reuse that image instead of exporting it repeatedly.

It starts six long-running services and runs two one-shot setup services:

| Long-running | Purpose |
| --- | --- |
| `minio` | Original files and a persistent notification queue |
| `event-handler` | MinIO notification to authenticated Airflow request |
| `airflow-api-server` | UI, REST API, and task execution API |
| `airflow-scheduler` | LocalExecutor and on-demand Spark subprocesses |
| `airflow-dag-processor` | DAG parsing |
| `airflow-db` | Airflow metadata PostgreSQL |

The one-shot setup jobs initialise Airflow and configure the MinIO bucket and
notification. Upload source files manually through the MinIO object browser.
Starting the stack does not run the generator or upload sample files.

The separate generator is an optional one-shot tool under the `tools` profile.
Its container/upload integration remains pending. Local services can run before
the ETL and Snowflake setup are complete; this does not make the pipeline ready
for end-to-end processing.

Local entry points use fixed host ports in `compose.yaml`:

Local demo logins are **admin / admin** for Airflow and its PostgreSQL metadata
database, and **admin / admin123** for MinIO (its password must have at least eight
characters). Airflow's admin, reviewer, and trigger settings use the same admin
account for this local demo. The Snowflake service user still uses its existing
key-pair authentication. The other containers have no separate user login.

To run only MinIO while developing notebooks, use `docker compose up -d --no-deps
minio`. This does not start Airflow or the notification handler. Local notebooks
use `http://localhost:19000` for the S3 API.

| Service | Host address | Container port |
| --- | --- | --- |
| Airflow UI/API | `http://localhost:18080` | 8080 |
| MinIO S3 API | `http://localhost:19000` | 9000 |
| MinIO object browser | `http://localhost:19001` | 9001 |
| Notification handler | Compose network only | 8000 |
| Airflow metadata PostgreSQL | Compose network only | 5432 |

The scheduler, DAG processor, one-shot jobs, and local Spark jobs have no published
host ports. Container-to-container URLs retain their internal ports.

Keep these host ports consistent across restarts. If a port is occupied, identify
its owner. Stop a stale SkyPoints process/container only after verifying ownership;
do not stop unrelated projects or silently choose a different port. Stopped
containers do not hold listening ports.

Published ports bind to localhost. No services are published to the Internet by
this setup.

## Storage and secrets

Named volumes preserve MinIO objects, pending notifications, Airflow metadata,
Airflow logs, and generator output. Normal `docker compose down` retains them;
`docker compose down -v` removes the volumes and their data.

Only the scheduler/task runtime receives the Snowflake key and connection settings.
The handler and generator do not receive Snowflake credentials. The generator's
input directory is mounted read-only. The local demo `.env` is tracked at the
project owner's request, so its generated credentials are part of Git history.
Private overrides, keys, and local datasets remain ignored. Environment files and
keys are excluded from Docker build contexts. Keep real Snowflake credentials in
the ignored override file or supply them through the shell environment.

The local bootstrap and Spark tasks currently share local MinIO credentials.
Hosted deployment should use a scoped ingestion identity, HTTPS, and deliberate
network exposure. Snowflake remains an external cloud service.

## Implementation sequence

1. Resolve the source-contract assumptions in `docs/source-contract.md`.
2. Implement Snowflake DDL and deterministic fixtures.
3. Implement Spark parsing, validation, derived fields, and JSON flattening.
4. Implement transactional latest-version/country publication.
5. Implement the notification bridge, delivery reconciliation, and generator.
6. Demonstrate replay, late delivery, country moves, and failure recovery.

The current DAG shows the proposed processing stages but fails with an explicit
implementation-pending error if manually triggered. The current HTTP receiver
returns a 503 for ingestion requests. Comment-only SQL files do not provision
warehouse objects. No source data is generated by the separate generator stub.

## Validation

Configuration can be checked without starting containers:

```sh
docker compose --env-file .env.example config --quiet
```

This checks configuration structure, not image builds, dependency installation,
service authentication, or Snowflake connectivity.

Local infrastructure verification completed on 2026-11-21:

- Built the MinIO, shared Airflow, and notification-handler images.
- Completed metadata migration, local Airflow user creation, and MinIO setup.
- Verified all six configured long-running services report healthy.
- Received HTTP 200 from MinIO readiness, its object browser, and Airflow health.
- Authenticated to Airflow and verified the ingestion DAG with zero import errors.
- Authenticated to MinIO and verified the landing bucket and notification filter.

No sample files were uploaded and no processing DAG was triggered. The HTTP
receiver and ETL remain placeholders; Snowflake connectivity and end-to-end
processing have not been tested. No triggerer service is deployed because the
current DAG has no deferrable tasks.

`requirements*.lock` pin direct dependencies; the Airflow environment additionally
uses upstream release constraints. They are not fully hash-locked dependency
exports. The JAR downloader verifies Maven-published checksums during image build.

## AI assistance

Codex assisted with the architecture review, folder scaffold, Docker/Compose
configuration, and bootstrap utilities. The implementation placeholders are
explicitly recorded above. Validation results should be added as functionality
is implemented and actually tested.

See `docs/design.md`, `docs/source-contract.md`, and `docs/demo.md` for decisions
and the planned evaluation flow.
