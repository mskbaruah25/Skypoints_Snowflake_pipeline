"""Key-pair connections and a read-only connection check.

Raw/staging transfer and transactional country publication remain pending.
"""

from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from skypoints.config import ConfigurationError, SnowflakeConfig

if TYPE_CHECKING:
    from snowflake.connector import SnowflakeConnection


def connect_snowflake(settings: SnowflakeConfig | None = None) -> "SnowflakeConnection":
    """Decrypt the key in memory and connect using the project's limited role."""
    settings = settings or SnowflakeConfig.from_environment()
    password = settings.private_key_passphrase
    try:
        key = serialization.load_pem_private_key(
            settings.private_key_file.read_bytes(),
            password=password.encode("utf-8") if password is not None else None,
        )
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            "Cannot decrypt the private key with the configured passphrase. Set "
            "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE in .env.local, or use --prompt."
        ) from exc
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
        raise ConfigurationError("This project requires an RSA private key of at least 2048 bits.")
    private_key = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    import snowflake.connector

    return snowflake.connector.connect(
        account=settings.account,
        user=settings.user,
        role=settings.role,
        warehouse=settings.warehouse,
        database=settings.database,
        schema=settings.schema,
        authenticator="SNOWFLAKE_JWT",
        private_key=private_key,
        login_timeout=20,
        network_timeout=30,
        session_parameters={"QUERY_TAG": "skypoints:connection"},
    )


def check_connection(settings: SnowflakeConfig | None = None) -> dict[str, object]:
    """Verify session identity and visibility of RAW, STAGING, and GOLD."""
    settings = settings or SnowflakeConfig.from_environment()
    with connect_snowflake(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), "
                "CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
                "CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            row = cursor.fetchone()
            if row is None:
                raise ConfigurationError("Snowflake returned no connection context.")
            organization, account, user, role, warehouse, database, schema = row
            expected = [
                settings.user, settings.role, settings.warehouse, settings.database, settings.schema
            ]
            actual = [user, role, warehouse, database, schema]
            if [str(v).upper() for v in actual] != [str(v).upper() for v in expected]:
                raise ConfigurationError("Connected session does not match the requested project context.")

            cursor.execute("SHOW SCHEMAS IN DATABASE IDENTIFIER(%s)", (settings.database,))
            columns = [column[0].lower() for column in cursor.description]
            name_index = columns.index("name")
            visible = {str(item[name_index]).upper() for item in cursor.fetchall()}
            required = {"RAW", "STAGING", "GOLD"}
            if not required.issubset(visible):
                missing = ", ".join(sorted(required - visible))
                raise ConfigurationError(f"Required schemas are not visible to the pipeline role: {missing}.")

    return {
        "status": "connected",
        "authentication": "key_pair",
        "account": f"{organization}-{account}",
        "user": user,
        "role": role,
        "warehouse": warehouse,
        "database": database,
        "schema": schema,
        "schemas_verified": sorted(required),
    }
