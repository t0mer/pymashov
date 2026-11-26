from dataclasses import dataclass, field
from typing import Optional
import httpx


@dataclass
class MashovSession:
    client: httpx.AsyncClient
    auth_token: str = field(repr=False)
    csrf_token: Optional[str] = field(repr=False)
