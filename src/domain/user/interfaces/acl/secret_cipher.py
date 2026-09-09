from typing import Protocol


class SecretCipherInterface(Protocol):
    """Reversible encryption for secrets that must be recoverable, not just verifiable.

    A TOTP seed cannot be hashed — the server has to reproduce it to check a code — so the
    only protection available at rest is encryption under a key kept outside the database.
    """

    def encrypt(self, plaintext: str) -> bytes: ...

    def decrypt(self, ciphertext: bytes) -> str: ...
