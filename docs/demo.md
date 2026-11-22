# Demonstration plan

The end-to-end demonstration is not implemented in the initial scaffold.

Once implemented:

1. Configure the local environment. Add Snowflake identity/objects before testing
   warehouse tasks; the local services can start without them.
2. Run `docker compose up --build -d`.
3. Inspect the generated member and JSON feeds in MinIO.
4. Follow the Airflow DAG, logs, row counts, and validation outcomes.
5. Query Snowflake RAW/STAGING and physical country/transaction tables.
6. Run a later delivery moving a member from India to the USA.
7. Replay the delivery and submit the older profile late; verify stable targets.
8. Inspect rejected records, transaction joins, and publication reconciliation.

The independent generator remains outside this repository. Its interface is the
source-file contract, not access to Snowflake. Reviewers need the local stack running
to upload into local MinIO. A future hosted deployment can run the same stack on a
server; this repository does not publish services automatically.
