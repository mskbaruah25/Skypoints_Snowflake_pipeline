# Design

## Processing boundary

The upstream source (or the separate test generator) delivers a member flat file
and redemption JSON to MinIO. The ETL starts at this delivery boundary.

The operator uploads complete member and redemption files to the landing bucket
root, enters a processing date in Airflow, and manually triggers `skypoints_ingestion`.
The date is a string in DDMMYYYY format. It labels the RAW delivery and selects the
corresponding partition in subsequent stages; it does not filter MinIO filenames.
Bucket notifications are disabled for this workflow.

Airflow controls three sequential tasks: `load_raw`, `load_staging`, and `load_gold`.
Each starts the isolated Python environment and uses Papermill to execute its
notebook in a fresh kernel. Papermill supplies the same partition date to each
notebook and saves an executed copy under the persistent Airflow logs volume.
The original notebooks are mounted read-only. LocalExecutor runs one task at a
time, with at most one active DAG run. Failed tasks block their downstream tasks.

Spark reads local MinIO and transfers data to Snowflake through the connector's
internally managed stage. GOLD uses the notebook's native Snowflake SQL connection.
Snowflake does not need direct access to the local MinIO endpoint.

## Publication

RAW publishes records and their batch fingerprint in one transaction. STAGING
refreshes the selected date's rows. GOLD uses country-specific MERGE statements and
the MEMBER_LOCATION registry to publish the latest eligible profiles, remove their
previous country entries, and update their location in one transaction. A failure
in GOLD does not roll back an earlier successful RAW or STAGING task.

Warehouse DDL is a separate setup step. The manual DAG does not create or reset
business tables. Complete batch replay protection is in RAW; record-level overlap
between different batches remains a validation concern in STAGING.

## Runtime and storage

One multi-target Dockerfile supplies the custom images. Default Compose startup
starts MinIO and its small one-shot bucket setup. The `airflow` profile adds
PostgreSQL, an API/UI server, a DAG processor, a scheduler, and a one-shot metadata
setup. The generator stays under the optional `tools` profile. Snowflake remains
external. PostgreSQL stores Airflow metadata only. Named volumes retain object data,
Airflow logs, metadata, and generator output across restarts.

Only the scheduler/task runtime has Snowflake credentials. DAG parsing does not
read credentials, open notebooks, or connect to MinIO or Snowflake. The notebook
runner rejects invalid dates and unprepared notebooks before executing any cells.
MinIO and Airflow communicate through the Compose network. Host-facing ports stay
fixed and bind to localhost.

## Demonstration versus production

The `local[1]` Spark layout with 512 MB driver heap is for bounded demonstrations.
It is not evidence of billion-record daily capacity. Production sizing must account
for file sizes, processing window, JSON expansion, country skew, and changed-member
volume. Use sharded deliveries, distributed Spark execution, bulk warehouse transfer,
and measured publication throughput for the production design.

Automatic landing-file archiving remains a separate implementation item. Keep only
the intended delivery at the bucket root; archive previous files outside that
landing bucket before supplying a new delivery.

## References

- https://airflow.apache.org/docs/apache-airflow/3.4.0/howto/docker-compose/index.html
- https://airflow.apache.org/docs/apache-airflow/3.4.0/core-concepts/params.html
- https://papermill.readthedocs.io/en/latest/usage-parameterize.html
- https://docs.snowflake.com/en/user-guide/spark-connector-overview
- https://docs.snowflake.com/en/sql-reference/transactions
- https://github.com/minio/minio/tree/RELEASE.2025-10-15T17-29-55Z
