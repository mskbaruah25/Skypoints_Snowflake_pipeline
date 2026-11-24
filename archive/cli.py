"""Local project status and read-only Snowflake connection checks."""

import argparse
from dataclasses import replace
import getpass
import json
import sys

from skypoints import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyPoints pipeline scaffold")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "command", choices=["status", "check-snowflake", "init-snowflake"], nargs="?", default="status"
    )
    parser.add_argument("--prompt", action="store_true", help="Prompt privately for the key passphrase.")
    args = parser.parse_args()
    if args.prompt and args.command != "check-snowflake":
        parser.error("--prompt is only used with check-snowflake.")
    if args.command == "init-snowflake":
        parser.error("Warehouse DDL and initialisation are not implemented in this scaffold.")
    if args.command == "check-snowflake":
        from snowflake.connector.errors import Error as SnowflakeError

        from skypoints.config import ConfigurationError, SnowflakeConfig
        from skypoints.snowflake import check_connection

        try:
            settings = SnowflakeConfig.from_environment()
            if args.prompt:
                if not sys.stdin.isatty():
                    parser.error("--prompt requires an interactive terminal.")
                settings = replace(
                    settings, private_key_passphrase=getpass.getpass("Private-key passphrase: ")
                )
            result = check_connection(settings)
        except ConfigurationError as exc:
            parser.exit(2, f"Configuration error: {exc}\n")
        except SnowflakeError as exc:
            parser.exit(
                1,
                f"Snowflake connection failed ({type(exc).__name__}, code {exc.errno}, "
                f"SQLSTATE {exc.sqlstate}). Check account, key registration, role, and network access.\n",
            )
        print(json.dumps(result, indent=2))
        return 0
    print(json.dumps({"version": __version__, "implementation": "scaffold", "etl_ready": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
