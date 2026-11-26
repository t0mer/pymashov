from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class MashovSession:
    csrf_header_token: str = field(repr=False)
    cookie_header: str = field(repr=False)
    base_url: str
    year: str
    mashov_auth_token: Optional[str] = field(default=None, repr=False)
    csrf_cookie_token: Optional[str] = field(default=None, repr=False)
