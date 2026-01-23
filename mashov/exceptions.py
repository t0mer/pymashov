class MashovError(Exception):
    """Base exception for pymashov."""


class MashovLoginError(MashovError):
    """Raised when login fails or required auth headers are missing."""


class MashovRequestError(MashovError):
    """Raised when an API request fails."""
