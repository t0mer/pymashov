from dataclasses import dataclass
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
