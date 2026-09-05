class HydraAdminError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code: int = status_code
        super().__init__(message)


class HydraChallengeNotFoundError(HydraAdminError):
    pass


class HydraChallengeGoneError(HydraAdminError):
    pass


class HydraClientNotFoundError(HydraAdminError):
    """Hydra has no such OAuth2 client.

    Translated to the port's `ProviderClientNotFoundError` at the adapter boundary, so a use
    case never has to know which authorization server is behind the port.
    """
