from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class MashovSession:
    client: httpx.AsyncClient
    auth_token: str
    csrf_token: Optional[str]