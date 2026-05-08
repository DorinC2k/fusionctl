class FusionctlError(Exception):
    """Base exception for expected CLI failures."""


class AuthenticationError(FusionctlError):
    """Raised when authentication is missing or invalid."""


class StorageError(FusionctlError):
    """Raised when local storage cannot be read or written."""


class OracleApiError(FusionctlError):
    """Raised when Oracle Fusion returns an API error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
