import bcrypt
from domain.user.interfaces import CryptInterface


class Crypt(CryptInterface):
    """
    Cryptography service using bcrypt.
    """

    def hash(self, pwd: str) -> bytes:
        return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt())

    def compare_hashes(self, plain_pwd: str, hashed_pwd: bytes) -> bool:
        return bcrypt.checkpw(plain_pwd.encode('utf-8'), hashed_pwd)
