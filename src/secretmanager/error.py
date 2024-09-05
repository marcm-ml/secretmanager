class BaseSecretError(RuntimeError):
    pass


class SecretNotFoundError(BaseSecretError):
    pass


class SecretAlreadyExistsError(BaseSecretError):
    pass
