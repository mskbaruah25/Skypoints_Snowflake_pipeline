# Tests

- `unit/`: pure parsing, validation, manifest identity, dates, and publication rules.
- `integration/`: MinIO, Airflow API, Spark/S3A, and real Snowflake boundaries.
- `e2e/`: file delivery through committed country and redemption outputs.
- `fixtures/`: small deterministic inputs and expected outcomes.

The initial scaffold does not contain ETL tests. Add tests with each implementation
step; do not report the empty test directories as a passing pipeline test suite.
