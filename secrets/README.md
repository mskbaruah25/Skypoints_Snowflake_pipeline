# Local secrets

Place the Snowflake private key here as `snowflake_key.p8` when warehouse tasks are
ready. `SNOWFLAKE_SECRETS_DIR` selects this host directory; Compose mounts it at
`/run/secrets` in the scheduler. `SNOWFLAKE_PRIVATE_KEY_FILE` is the path inside that
container, normally `/run/secrets/snowflake_key.p8`. Set real Snowflake connection
values in the ignored `.env.local` override.
Select that override with `docker compose --env-file .env.local ...`.

For local Python and notebooks, set `SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE` to the host
key path in `.env.local`. The connection helper uses this host-specific setting
locally; Compose passes only the container key path to the scheduler. Set
`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` privately in the override, or use the local CLI's
`check-snowflake --prompt` option for an interactive check.

Git ignores every file in this directory except this README. Docker excludes the
entire directory from image build contexts. Compose mounts the directory read-only
into the scheduler/task runtime. The key may be absent during infrastructure startup.
No Snowflake private key is included in the repository.
