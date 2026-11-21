# Local secrets

Place the Snowflake private key here as `snowflake_key.p8`, or set
`SNOWFLAKE_PRIVATE_KEY_FILE` in the ignored `.env.local` override to its actual path.
Select that override with `docker compose --env-file .env.local ...`.

Git ignores every file in this directory except this README. Docker excludes the
entire directory from image build contexts. Compose mounts the key read-only into
the scheduler/task runtime. No Snowflake private key is included in the repository.
