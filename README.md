# SkyPoints pipeline

Initial project scaffold for the Incubyte data-engineering assessment.

**Status:** the folder layout, single multi-target Dockerfile, Compose definitions,
dependency specifications, and local bootstrap utilities are present. ETL logic,
warehouse DDL/publication SQL, the notification bridge, and the separate generator
are implementation placeholders. The pipeline is not yet an end-to-end demo.
Placeholder entry points fail explicitly rather than reporting successful work.

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

## Setup and intended startup

Requirements: Docker with Compose 2.17+ and BuildKit, an existing Snowflake account,
and a private key for the pipeline identity.

1. Copy `.env.example` to `.env` and replace its placeholders. Keep `.env` private.
2. Put the Snowflake key at the configured path, normally `secrets/snowflake_key.p8`.
3. Set `DATA_GENERATOR_DIR` if the sibling generator is stored somewhere else.
4. Complete the implementation items listed below before attempting a full demo.

The intended one-command startup, after implementation and warehouse setup, is:

```sh
docker compose up --build -d
```

It starts six long-running services and runs three one-shot services:

| Long-running | Purpose |
| --- | --- |
| `minio` | Original files and a persistent notification queue |
| `event-handler` | MinIO notification to authenticated Airflow request |
| `airflow-api-server` | UI, REST API, and task execution API |
| `airflow-scheduler` | LocalExecutor and on-demand Spark subprocesses |
| `airflow-dag-processor` | DAG parsing |
| `airflow-db` | Airflow metadata PostgreSQL |

The one-shot jobs initialise Airflow, configure the MinIO bucket/notification, and
run the separate generator. A completed generator exits normally; it is not an
always-running data service. Its implementation is still pending in this commit.

Local entry points are Airflow at `http://localhost:8080`, MinIO's S3 API at
`http://localhost:9000`, and MinIO's object browser at `http://localhost:9001`.
Ports bind to localhost. No services are published to the Internet by this setup.

## Storage and secrets

Named volumes preserve MinIO objects, pending notifications, Airflow metadata,
Airflow logs, and generator output. Normal `docker compose down` retains them;
`docker compose down -v` removes the volumes and their data.

Only the scheduler/task runtime receives the Snowflake key and connection settings.
The handler and generator do not receive Snowflake credentials. The generator's
input directory is mounted read-only. Real credentials and local datasets are
excluded from Git and Docker build contexts.

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
service authentication, or Snowflake connectivity. Container builds and live
integration tests have not been performed for this scaffold.

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
