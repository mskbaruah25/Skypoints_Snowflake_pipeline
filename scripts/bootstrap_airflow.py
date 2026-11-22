"""Synchronise local FAB logins after metadata migrations."""

import json
import os
import subprocess


def main() -> None:
    result = subprocess.run(
        ["airflow", "users", "list", "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    existing = {user["username"] for user in json.loads(result.stdout)}
    configured = {}
    for prefix, default_name, role in [
        ("AIRFLOW_ADMIN", "admin", "Admin"),
        ("AIRFLOW_REVIEWER", "admin", "Viewer"),
        ("AIRFLOW_TRIGGER", "admin", "User"),
    ]:
        username = os.environ.get(f"{prefix}_USERNAME", default_name)
        password = os.environ[f"{prefix}_PASSWORD"]
        if not username or not password or password.startswith("REPLACE_"):
            raise ValueError(f"Provide real local credentials for {prefix} before initialisation.")
        if username in configured:
            if configured[username] != password:
                raise ValueError(f"Conflicting passwords configured for Airflow user {username}.")
            continue
        configured[username] = password
        if username in existing:
            subprocess.run(
                ["airflow", "users", "reset-password", "--username", username, "--password", password],
                check=True,
            )
            continue
        subprocess.run(
            [
                "airflow", "users", "create",
                "--username", username,
                "--password", password,
                "--firstname", "SkyPoints",
                "--lastname", role,
                "--role", role,
                "--email", f"{default_name}@example.invalid",
            ],
            check=True,
        )
        existing.add(username)


if __name__ == "__main__":
    main()
