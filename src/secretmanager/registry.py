import importlib.util
import shutil
import types
from collections.abc import Callable
from random import choice

from secretmanager.implementations.aws import AWSSecretStore
from secretmanager.implementations.dotenv import DotEnvStore
from secretmanager.implementations.env import EnvVarStore
from secretmanager.implementations.sops import SOPSSecretStore
from secretmanager.settings import Settings, StoreChoice
from secretmanager.store import AbstractSecretStore

# hugely inspired by fsspec registry implementation

_registry: dict[str, Callable[..., AbstractSecretStore]] = {}
registry = types.MappingProxyType(_registry)


def register_implementation(name: str, implementation: Callable[..., AbstractSecretStore], replace=False):
    if name in registry and replace is False:
        if _registry[name] is not implementation:
            raise ValueError(f"Name ({name}) already in the registry and replace is False")
    else:
        _registry[name] = implementation


def get_store_class(implementation: str | StoreChoice) -> Callable[..., AbstractSecretStore]:
    if isinstance(implementation, StoreChoice):
        implementation = implementation.value

    if implementation in registry:
        return registry[implementation]
    else:
        msg = f"Store {choice} is not registered."
        if choice in _known_implementations:
            msg += " " + _known_implementations[choice]["error"]
        raise NotImplementedError(msg)


def get_store(implementation: str | StoreChoice, **kwargs) -> AbstractSecretStore:
    return get_store_class(implementation)(**kwargs)


_known_implementations = {
    StoreChoice.AWS.value: {
        "dependency": "pip intsall secretmanager[aws]",
        "error": "Install required dependencies via secretmanager[aws]",
    },
    StoreChoice.AZURE.value: {
        "dependency": "pip intsall secretmanager[azure]",
        "error": "Install required dependencies via secretmanager[azure]",
    },
    StoreChoice.BITWARDEN.value: {
        "dependency": "pip intsall secretmanager[bitwarden]",
        "error": "Install required dependencies via secretmanager[bitwarden]",
    },
    StoreChoice.DOTENV.value: {
        "dependency": "pip intsall secretmanager[dotenv]",
        "error": "Install required dependencies via secretmanager[dotenv]",
    },
    StoreChoice.GOOGLE.value: {
        "dependency": "pip intsall secretmanager[gc]",
        "error": "Install required dependencies via secretmanager[gc]",
    },
    StoreChoice.SOPS.value: {
        "dependency": "Install sops binary @ https://github.com/getsops/sops/releases",
        "error": (
            "Make sure the `sops` binary is installed and available via PATH. "
            "Alternatively set the store setting `binary` to the appropiate path."
        ),
    },
}

register_implementation(StoreChoice.ENV.value, EnvVarStore)
if importlib.util.find_spec("dotenv"):
    register_implementation(StoreChoice.DOTENV.value, DotEnvStore)
if importlib.util.find_spec("botocore"):
    register_implementation(StoreChoice.AWS.value, AWSSecretStore)
if shutil.which(Settings.sops.binary or "sops"):
    register_implementation(StoreChoice.SOPS.value, SOPSSecretStore)
