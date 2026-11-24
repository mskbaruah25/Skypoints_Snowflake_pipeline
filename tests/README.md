# Tests

- `unit/`: connection configuration, date validation, and notebook orchestration.
- `integration/`: MinIO, Airflow API, Spark/S3A, and real Snowflake boundaries.
- `e2e/`: file delivery through committed country and redemption outputs.
- `fixtures/`: small deterministic inputs and expected outcomes.

The tests cover connection setup and manual notebook orchestration. They do not
prove the complete Spark/MinIO/Snowflake data flow.

Snowflake connection unit tests now cover configuration precedence, literal secret
handling, encrypted-key validation, and in-memory key-pair connection parameters.
Run them with `python -m pytest -q tests/unit/test_snowflake_connection.py`.
They use temporary test keys and do not connect to Snowflake. The separate
`python -m skypoints.cli check-snowflake` command performs a live read-only check.

`unit/test_notebook_orchestration.py` checks date validation, required trigger
parameters, task ordering, serial execution, and the preflight check for notebooks
that have not been prepared for parameter injection.

`integration/test_notebook_execution.py` executes tiny temporary notebooks with
real local Python kernels. It checks date injection (including leading zeroes),
retry output separation, source-file preservation, and error propagation. These
tests do not start Spark, Docker, or Snowflake. The `skypoints` kernel must be
registered and local Jupyter loopback ports must be permitted.
