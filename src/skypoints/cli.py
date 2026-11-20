"""Local project CLI; warehouse setup is deliberately not implemented yet."""

import argparse
import json

from skypoints import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="SkyPoints pipeline scaffold")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("command", choices=["status", "init-snowflake"], nargs="?", default="status")
    args = parser.parse_args()
    if args.command == "init-snowflake":
        parser.error("Warehouse DDL and initialisation are not implemented in this scaffold.")
    print(json.dumps({"version": __version__, "implementation": "scaffold", "etl_ready": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
