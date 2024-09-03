class BaseSecretError(RuntimeError):
    pass


class SecretNotFoundError(BaseSecretError):
    pass


class SecretAlreadyExists(BaseSecretError):
    pass
