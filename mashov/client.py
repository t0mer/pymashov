from __future__ import annotations

from typing import Any, Optional, Dict
import httpx

from .exceptions import MashovLoginError, MashovRequestError
from .models import MashovSession

DEFAULT_BASE_URL = "https://web.mashov.info"


def _build_cookie_header(jar: httpx.Cookies) -> str:
    return "; ".join(f"{k}={v}" for k, v in jar.items())


class MashovClient:
    def __init__(
        self,
        username: str,
        password: str,
        semel: str,
        *,
        year: str = "2026",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        auto_login: bool = True,
    ):
        self._username = username
        self._password = password
        self._semel = semel
        self._year = str(year)
        self._base_url = base_url.rstrip("/")
        self._auto_login = auto_login

        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )

        self._session: Optional[MashovSession] = None

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "MashovClient":
        # don't force login — let user choose
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def is_logged_in(self) -> bool:
        return self._session is not None

    @property
    def session(self) -> MashovSession:
        if not self._session:
            raise MashovLoginError("Not logged in. Call await client.login() first.")
        return self._session

    async def login(self) -> MashovSession:
        """
        Login ONLY. Does not call any other endpoint.
        """
        resp = await self._http.post(
            "/api/login",
            json={
                "username": self._username,
                "password": self._password,
                "semel": self._semel,
                "year": self._year,
            },
        )

        if resp.status_code >= 400:
            raise MashovLoginError(f"Login failed ({resp.status_code}): {resp.text}")

        csrf_header_token = resp.headers.get("x-csrf-token")
        if not csrf_header_token:
            raise MashovLoginError("Login response missing 'x-csrf-token' header")

        cookie_header = _build_cookie_header(self._http.cookies)
        if not cookie_header:
            raise MashovLoginError("Login did not set cookies (cookie jar is empty)")

        self._session = MashovSession(
            csrf_header_token=csrf_header_token,
            cookie_header=cookie_header,
            base_url=self._base_url,
            year=self._year,
            mashov_auth_token=self._http.cookies.get("MashovAuthToken"),
            csrf_cookie_token=self._http.cookies.get("Csrf-Token"),
        )
        return self._session

    async def ensure_logged_in(self) -> None:
        """
        Ensures we have an auth session.
        If auto_login=False, this will raise instead.
        """
        if self._session:
            return
        if not self._auto_login:
            raise MashovLoginError("Not logged in and auto_login=False. Call await client.login().")
        await self.login()

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Low-level request method so ANY API endpoint can be called separately.
        """
        await self.ensure_logged_in()
        assert self._session is not None

        final_headers: Dict[str, str] = {}
        if headers:
            final_headers.update(headers)

        final_headers["X-Csrf-Token"] = self._session.csrf_header_token

        # Optional: you can rely on the cookie jar, but you asked to attach it explicitly.
        final_headers["Cookie"] = self._session.cookie_header

        resp = await self._http.request(method, path, headers=final_headers, **kwargs)

        if resp.status_code >= 400:
            raise MashovRequestError(f"{method} {path} failed ({resp.status_code}): {resp.text}")

        return resp

    async def public_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make a request that does NOT require authentication.
        """
        final_headers: Dict[str, str] = {}
        if headers:
            final_headers.update(headers)

        resp = await self._http.request(
            method,
            path,
            headers=final_headers,
            **kwargs,
        )

        if resp.status_code >= 400:
            raise MashovRequestError(
                f"{method} {path} failed ({resp.status_code}): {resp.text}"
            )

        return resp

    # ---- Example endpoint wrapper ----
    async def get_grades(self, student_id: str) -> Any:
        resp = await self.request("GET", f"/api/students/{student_id}/grades")
        return resp.json()

    async def get_schools(self) -> Any:
        resp = await self.public_request("GET", "/api/schools")
        return resp.json()

    async def get_conversations(
        self,
        *,
        skip: int = 0,
        take: int = 20,
    ) -> Any:
        resp = await self.request(
            "GET",
            "/api/mail/inbox/conversations",
            params={
                "skip": skip,
                "take": take,
            },
        )
        return resp.json()
    
    async def get_timetable(self, student_id: str) -> Any:
        """
        Get timetable for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        path = f"/api/students/{student_id}/timetable"

        resp = await self.request("GET", path)
        return resp.json()
    

    async def get_homework(self, student_id: str) -> Any:
        """
        Get homework for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        path = f"/api/students/{student_id}/homework"

        resp = await self.request("GET", path)
        return resp.json()
    
    
    async def get_behavior(self, student_id: str) -> Any:
        """
        Get behavior/discipline records for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        path = f"/api/students/{student_id}/behave"

        resp = await self.request("GET", path)
        return resp.json()