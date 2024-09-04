import types
from collections.abc import Callable

from .implementations.aws import AWSSecretStore
from .implementations.dotenv import DotEnvStore
from .implementations.env import EnvVarStore
from .settings import StoreChoice
from .store import AbstractSecretStore

_registry: dict[str, Callable[..., AbstractSecretStore]] = {}
registry = types.MappingProxyType(_registry)


def register_implementation(name: str, cls: Callable[..., AbstractSecretStore], replace=False):
    if name in registry and replace is False:
        if _registry[name] is not cls:
            raise ValueError(f"Name ({name}) already in the registry and replace is False")
    else:
        _registry[name] = cls


def get_store(choice: str | StoreChoice, **kwargs) -> AbstractSecretStore:
    if isinstance(choice, StoreChoice):
        choice = choice.value

    if choice == StoreChoice.ENV.value:
        return EnvVarStore(**kwargs)
    elif choice == StoreChoice.DOTENV.value:
        return DotEnvStore(**kwargs)
    elif choice == StoreChoice.AWS.value:
        return AWSSecretStore(**kwargs)
    elif choice == StoreChoice.AZURE.value:
        raise NotImplementedError()
    elif choice == StoreChoice.BITWARDEN.value:
        raise NotImplementedError()
    elif choice == StoreChoice.GOOGLE.value:
        raise NotImplementedError()
    elif choice in registry:
        return registry[choice](**kwargs)
    else:
        raise NotImplementedError()
