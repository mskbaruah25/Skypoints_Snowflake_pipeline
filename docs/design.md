# Design

## Processing boundary

The upstream source (or the separate test generator) delivers a member flat file
and redemption JSON to MinIO. The ETL starts at this delivery boundary.

MinIO notifications identify ready manifests. A small HTTP receiver translates a
notification into an authenticated Airflow DAG run. It uses deterministic batch
identity to recognise repeated notifications. A planned reconciliation job recovers
ready deliveries whose notifications were missed.

Airflow controls dependencies and retries. LocalExecutor starts on-demand Spark
subprocesses in the scheduler container. Spark reads MinIO and writes raw/staging
Snowflake tables through the connector's internally managed transfer stage.
Snowflake does not need direct access to the local MinIO endpoint.

## Publication

After all required staging writes succeed, a final warehouse transaction resolves
newer member versions globally, updates the canonical member, removes old-country
entries, upserts destination entries, and records successful publication. New
country-table DDL must be outside this transaction. Retries must preserve results.

## Runtime and storage

One multi-target Dockerfile builds the four custom images. Compose starts six
long-running services and two one-shot setup jobs. The generator is an optional
tool under the `tools` profile; it does not run during normal startup. Snowflake
remains external, and its key is not required to start the local services.
PostgreSQL is used only for Airflow metadata. Docker volumes retain object data,
pending notifications, logs, metadata, and generator output across restarts.

Only the scheduler/task runtime has Snowflake credentials. Configuration parsing
must not require warehouse credentials at DAG import time. MinIO, the handler,
and Airflow communicate through the Compose network. Host-facing ports are local.

## Demonstration versus production

The initial `local[2]` Spark layout is for bounded correctness demonstrations.
It is not evidence of billion-record daily capacity. Production sizing must account
for file sizes, processing window, JSON expansion, country skew, and changed-member
volume. Use sharded deliveries, distributed Spark execution, bulk warehouse transfer,
and measured publication throughput for the production design.

The pinned MinIO Community source is archived upstream. It is retained as the agreed
demonstration dependency, not presented as a maintained production recommendation.

## References

- https://airflow.apache.org/docs/apache-airflow/3.4.0/howto/docker-compose/index.html
- https://docs.snowflake.com/en/user-guide/spark-connector-overview
- https://docs.snowflake.com/en/sql-reference/transactions
- https://github.com/minio/minio/tree/RELEASE.2025-10-15T17-29-55Z
