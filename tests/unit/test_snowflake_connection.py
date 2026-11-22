from dataclasses import replace
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from skypoints.config import ConfigurationError, SnowflakeConfig
from skypoints.snowflake import connect_snowflake


@pytest.fixture
def key_settings(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    password = "test-key-passphrase-only"
    path = tmp_path / "key.p8"
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password.encode()),
    ))
    return key, SnowflakeConfig(
        account="ORG-ACCOUNT", user="PIPELINE", role="PIPELINE_ROLE",
        warehouse="PIPELINE_WH", database="SKYPOINTS", schema="RAW",
        private_key_file=path, private_key_passphrase=password,
    )


def test_private_override_and_process_precedence_preserve_literal_passphrase(tmp_path):
    (tmp_path / "key.p8").touch()
    (tmp_path / ".env").write_text(
        "SNOWFLAKE_ACCOUNT=ORG-ACCOUNT\nSNOWFLAKE_USER=DEFAULT_USER\n"
        "SNOWFLAKE_ROLE=PIPELINE_ROLE\nSNOWFLAKE_WAREHOUSE=PIPELINE_WH\n"
        "SNOWFLAKE_DATABASE=SKYPOINTS\nSNOWFLAKE_PRIVATE_KEY_FILE=/run/secrets/key.p8\n"
    )
    (tmp_path / ".env.local").write_text(
        "SNOWFLAKE_USER=LOCAL_USER\nSNOWFLAKE_LOCAL_PRIVATE_KEY_FILE=key.p8\n"
        "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE='literal${NOT_AN_ENV_VAR}'\n"
    )
    settings = SnowflakeConfig.from_environment(
        project_root=tmp_path, environ={"SNOWFLAKE_USER": "PROCESS_USER"}
    )
    assert settings.user == "PROCESS_USER"
    assert settings.private_key_file == tmp_path / "key.p8"
    assert settings.private_key_passphrase == "literal${NOT_AN_ENV_VAR}"
    assert settings.private_key_passphrase not in repr(settings)


def test_container_environment_does_not_depend_on_local_override_files(key_settings, tmp_path):
    _, original = key_settings
    values = {
        "SNOWFLAKE_ACCOUNT": original.account,
        "SNOWFLAKE_USER": original.user,
        "SNOWFLAKE_ROLE": original.role,
        "SNOWFLAKE_WAREHOUSE": original.warehouse,
        "SNOWFLAKE_DATABASE": original.database,
        "SNOWFLAKE_PRIVATE_KEY_FILE": str(original.private_key_file),
    }
    settings = SnowflakeConfig.from_environment(project_root=tmp_path, environ=values)
    assert settings.private_key_file == original.private_key_file
    assert settings.private_key_passphrase is None


@pytest.mark.parametrize("password", [None, "incorrect-test-passphrase"])
def test_bad_or_missing_passphrase_fails_before_network(key_settings, monkeypatch, password):
    _, settings = key_settings
    network = Mock()
    monkeypatch.setattr("snowflake.connector.connect", network)
    with pytest.raises(ConfigurationError, match="passphrase") as caught:
        connect_snowflake(replace(settings, private_key_passphrase=password))
    network.assert_not_called()
    if password:
        assert password not in str(caught.value)


def test_valid_key_is_decrypted_in_memory_and_service_role_is_explicit(key_settings, monkeypatch):
    original, settings = key_settings
    connection = object()
    network = Mock(return_value=connection)
    monkeypatch.setattr("snowflake.connector.connect", network)
    assert connect_snowflake(settings) is connection
    options = network.call_args.kwargs
    restored = serialization.load_der_private_key(options["private_key"], password=None)
    assert restored.public_key().public_numbers() == original.public_key().public_numbers()
    assert options["authenticator"] == "SNOWFLAKE_JWT"
    assert options["user"] == settings.user
    assert options["role"] == settings.role
    assert "password" not in options
    assert settings.private_key_passphrase not in options.values()


def test_placeholder_configuration_fails_with_setting_name_only(tmp_path):
    with pytest.raises(ConfigurationError, match="SNOWFLAKE_ACCOUNT"):
        SnowflakeConfig.from_environment(
            project_root=tmp_path, environ={"SNOWFLAKE_ACCOUNT": "REPLACE_ACCOUNT"}
        )
