import types
from collections.abc import Callable

from secretmanager.implementations.aws import AWSSecretStore
from secretmanager.implementations.dotenv import DotEnvStore
from secretmanager.implementations.env import EnvVarStore
from secretmanager.implementations.sops import SOPSSecretStore
from secretmanager.settings import StoreChoice
from secretmanager.store import AbstractSecretStore

_registry: dict[str, Callable[..., AbstractSecretStore]] = {}
registry = types.MappingProxyType(_registry)

_registry[StoreChoice.ENV.value] = EnvVarStore
_registry[StoreChoice.DOTENV.value] = DotEnvStore
_registry[StoreChoice.AWS.value] = AWSSecretStore
_registry[StoreChoice.SOPS.value] = SOPSSecretStore


def register_implementation(name: str, implementation: Callable[..., AbstractSecretStore], replace=False):
    if name in registry and replace is False:
        if _registry[name] is not implementation:
            raise ValueError(f"Name ({name}) already in the registry and replace is False")
    else:
        _registry[name] = implementation


def get_store(implementation: str | StoreChoice, **kwargs) -> AbstractSecretStore:
    if isinstance(implementation, StoreChoice):
        implementation = implementation.value

    if implementation in registry:
        return registry[implementation](**kwargs)
    else:
        raise NotImplementedError()
