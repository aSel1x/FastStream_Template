import base64
import hashlib
import os
from typing import ClassVar, final, override

from cryptography.fernet import Fernet, InvalidToken

from application.common.exceptions import BaseApplicationError, ConfigurationError
from domain.user.interfaces.acl.secret_cipher import SecretCipherInterface

SECRET_ENCRYPTION_KEY_VAR = 'SECRET_ENCRYPTION_KEY'  # noqa: S105 - a variable name


@final
class SecretDecryptionError(BaseApplicationError):
    """A stored secret could not be decrypted with the configured key."""

    status: ClassVar[int] = 500

    @property
    @override
    def detail(self) -> str:
        return (
            'A stored secret could not be decrypted. This means '
            f'{SECRET_ENCRYPTION_KEY_VAR} has changed since it was written.'
        )


@final
class FernetSecretCipher(SecretCipherInterface):
    """Fernet (AES-128-CBC + HMAC) over a key derived from `SECRET_ENCRYPTION_KEY`.

    Rotating the key invalidates every stored secret, so 2FA would have to be re-enrolled;
    a real deployment should hold the key in a KMS or secret manager, not in an env var.
    """

    def __init__(self, key: str) -> None:
        if not key or len(key) < 32:
            message = (
                f'{SECRET_ENCRYPTION_KEY_VAR} must be at least 32 characters. '
                'Generate one with: openssl rand -hex 32'
            )
            raise ConfigurationError(message)
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        self._fernet = Fernet(derived)

    @classmethod
    def from_environ(cls) -> FernetSecretCipher:
        return cls(os.getenv(SECRET_ENCRYPTION_KEY_VAR, ''))

    @override
    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    @override
    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise SecretDecryptionError() from exc
