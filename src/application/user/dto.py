import datetime as dt
from dataclasses import dataclass
from uuid import UUID


@dataclass
class UserDTO:
    uuid: UUID
    username: str
    is_active: bool
    hashed_password: bytes
    created_at: dt.datetime
    updated_at: dt.datetime
