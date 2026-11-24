"""Load connection settings at execution time, never during DAG parsing."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(ValueError):
    """Missing or invalid local connection settings."""


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    role: str
    warehouse: str
    database: str
    schema: str
    private_key_file: Path
    private_key_passphrase: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(
        cls,
        *,
        project_root: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "SnowflakeConfig":
        root = project_root if project_root is not None else PROJECT_ROOT
        process = os.environ if environ is None else environ
        values: dict[str, str] = {}
        for filename in [".env", ".env.local"]:
            path = root / filename
            if path.is_file():
                # Local development uses dotenv; containers receive environment
                # variables directly and do not contain these private files.
                from dotenv import dotenv_values

                values.update(
                    {k: v for k, v in dotenv_values(path, interpolate=False).items() if v is not None}
                )
        values.update(process)

        def required(name: str) -> str:
            value = values.get(name, "").strip()
            if not value or value.startswith("REPLACE_"):
                raise ConfigurationError(f"Configure {name} in the private .env.local file.")
            return value

        account = required("SNOWFLAKE_ACCOUNT")
        if "://" in account or account.lower().endswith(".snowflakecomputing.com"):
            raise ConfigurationError("SNOWFLAKE_ACCOUNT must be an organization-account identifier.")

        key_location = (
            process.get("SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE")
            or process.get("SNOWFLAKE_PRIVATE_KEY_FILE")
            or values.get("SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE")
            or required("SNOWFLAKE_PRIVATE_KEY_FILE")
        )
        key_file = Path(key_location).expanduser()
        if not key_file.is_absolute():
            key_file = root / key_file
        if not key_file.is_file():
            raise ConfigurationError("The configured Snowflake private-key file does not exist.")

        return cls(
            account=account,
            user=required("SNOWFLAKE_USER"),
            role=required("SNOWFLAKE_ROLE"),
            warehouse=required("SNOWFLAKE_WAREHOUSE"),
            database=required("SNOWFLAKE_DATABASE"),
            schema=values.get("SNOWFLAKE_SCHEMA") or "RAW",
            private_key_file=key_file,
            private_key_passphrase=values.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
        )
