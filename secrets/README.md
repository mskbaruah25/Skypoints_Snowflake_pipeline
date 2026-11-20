# Local secrets

Place the Snowflake private key here as `snowflake_key.p8`, or set
`SNOWFLAKE_PRIVATE_KEY_FILE` in the private `.env` to its actual path.

Git ignores every file in this directory except this README. Docker excludes the
entire directory from image build contexts. Compose mounts the key read-only into
the scheduler/task runtime. No real key or credentials are included in the scaffold.
