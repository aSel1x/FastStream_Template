class HydraAdminError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code: int = status_code
        super().__init__(message)


class HydraChallengeNotFoundError(HydraAdminError):
    pass


class HydraChallengeGoneError(HydraAdminError):
    pass


class HydraClientNotFoundError(HydraAdminError):
    pass
