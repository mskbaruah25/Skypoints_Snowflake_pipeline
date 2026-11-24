# Tests

- `unit/`: date validation and notebook orchestration.
- `integration/`: MinIO, Airflow API, Spark/S3A, and real Snowflake boundaries.
- `e2e/`: file delivery through committed country and redemption outputs.
- `fixtures/`: small deterministic inputs and expected outcomes.

The tests cover date validation and manual notebook orchestration. They do not
prove the complete Spark/MinIO/Snowflake data flow.

The retired standalone Snowflake connection helpers and their corresponding test
are kept in `../archive/`. They are reference material outside this active suite.

`unit/test_notebook_orchestration.py` checks date validation, required trigger
parameters, task ordering, serial execution, and the preflight check for notebooks
that have not been prepared for parameter injection.

`integration/test_notebook_execution.py` executes tiny temporary notebooks with
real local Python kernels. It checks date injection (including leading zeroes),
retry output separation, source-file preservation, and error propagation. These
tests do not start Spark, Docker, or Snowflake. The `skypoints` kernel must be
registered and local Jupyter loopback ports must be permitted.
