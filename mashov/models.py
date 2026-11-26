from dataclasses import dataclass, field
from typing import Optional
import httpx


@dataclass(frozen=True)
class MashovSession:
    csrf_header_token: str        # from response header x-csrf-token
    cookie_header: str            # "a=b; c=d"
    base_url: str
    year: str

    # optional: keep for debugging
    mashov_auth_token: Optional[str] = None
    csrf_cookie_token: Optional[str] = None


@dataclass(frozen=True)
class MashovChild:
    """A child accessible to the signed-in parent account."""

    child_guid: str = field(repr=False)
    private_name: str = field(repr=False)
    family_name: str = field(default="", repr=False)
