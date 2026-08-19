from typing import override

import pyotp
from domain.user.interfaces import TwoFactorInterface


class TwoFactorAuth(TwoFactorInterface):
    @override
    def generate_secret(self) -> str:
        return pyotp.random_base32()

    @override
    def get_provisioning_uri(self, secret: str, username: str, issuer: str = 'BackendTemplate') -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)

    @override
    def verify_code(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
