import pytest

from secretmanager.error import SecretNotFoundError
from secretmanager.implementations.sops import SOPSSecretStore


@pytest.fixture
def sops_file(tmp_path):
    path = tmp_path / "env.yaml"
    path.touch()
    return path


@pytest.fixture(autouse=True)
def _set_sops_binary(monkeypatch):
    monkeypatch.setattr("secretmanager.implementations.sops._get_sops_version", lambda x: "3.0.0")
    monkeypatch.setattr("secretmanager.implementations.sops._sops", True)


@pytest.fixture
def store(monkeypatch, sops_file) -> SOPSSecretStore:
    monkeypatch.setattr(
        "secretmanager.implementations.sops.SOPSSecretStore._decrypt",
        lambda x: b'{"KEY": "VALUE", "TEST": {"key": "value"}}',
    )
    return SOPSSecretStore(sops_file).__deepcopy__()


def test_binary_not_available(monkeypatch, sops_file):
    monkeypatch.setattr("secretmanager.implementations.sops._sops", False)
    with pytest.raises(RuntimeError, match="Cannot find `sops` command anywhere on PATH"):
        SOPSSecretStore(sops_file)


def test_version_invalid(monkeypatch, sops_file):
    monkeypatch.setattr("secretmanager.implementations.sops._get_sops_version", lambda x: "2.0.0")
    with pytest.raises(ValueError, match="Sops version 2.0.0 is not supported"):
        SOPSSecretStore(sops_file)


def test_inplace_option(sops_file):
    with pytest.raises(ValueError, match="Inplace decryption is not supported"):
        SOPSSecretStore(sops_file, sops_options=["--in-place"])
    with pytest.raises(ValueError, match="Inplace decryption is not supported"):
        SOPSSecretStore(sops_file, sops_options=["-i"])


def test_output_type_option(sops_file):
    with pytest.raises(ValueError, match="Argument --output-type is not supported"):
        SOPSSecretStore(sops_file, sops_options=["--output-type"])


def test_getting_missing(store):
    with pytest.raises(SecretNotFoundError, match="was not found in"):
        store.get("123")


def test_getting(store):
    val = store.get("KEY")

    assert val.get_secret_value() == "VALUE"


def test_list_secret_keys(store):
    secrets = store.list_secret_keys()

    assert "KEY" in secrets
    assert "TEST" in secrets


def test_list_secrets(store):
    secrets = store.list_secrets()

    assert "KEY" in secrets
    assert secrets["KEY"].get_secret_value() == "VALUE"
    assert "TEST" in secrets
    assert secrets["TEST"].get_secret_value() == {"key": "value"}
