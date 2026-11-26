from __future__ import annotations

import logging
from typing import Any, Optional, Dict
import httpx

from .exceptions import MashovLoginError, MashovRequestError
from .models import MashovSession

logger = logging.getLogger(__name__)

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
        origin = httpx.URL(base_url)
        if (origin.scheme != "https" or origin.host != "web.mashov.info"
                or origin.port not in (None, 443) or origin.userinfo
                or origin.path != "/" or origin.query or origin.fragment):
            raise ValueError("Expected the Mashov HTTPS origin.")
        self._base_url = DEFAULT_BASE_URL
        self._auto_login = auto_login

        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
            follow_redirects=False,
            trust_env=False,
        )

        self._session: Optional[MashovSession] = None

    async def close(self) -> None:
        """Close the HTTP client connection."""
        logger.debug("Closing HTTP client connection")
        await self._http.aclose()
        logger.info("HTTP client connection closed successfully")

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

        try:
            resp = await self._http.post(
                "/api/login",
                json={
                    "username": self._username,
                    "password": self._password,
                    "semel": self._semel,
                    "year": self._year,
                },
            )

        except httpx.TimeoutException:

            raise MashovLoginError("Login request timed out") from None
        except httpx.RequestError:

            raise MashovLoginError("Login request failed") from None

        if not resp.is_success:

            raise MashovLoginError(f"Login failed ({resp.status_code})")

        csrf_header_token = resp.headers.get("x-csrf-token")
        if not csrf_header_token:
            logger.error("Login response missing 'x-csrf-token' header")
            raise MashovLoginError("Login response missing 'x-csrf-token' header")

        cookie_header = _build_cookie_header(self._http.cookies)
        if not cookie_header:
            logger.error("Login did not set cookies (cookie jar is empty)")
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
            logger.debug("Already logged in, session exists")
            return
        if not self._auto_login:
            logger.warning("Not logged in and auto_login is disabled")
            raise MashovLoginError("Not logged in and auto_login=False. Call await client.login().")
        logger.info("Auto-login triggered")
        await self.login()

    @staticmethod
    def _validate_request(path: str, options: dict) -> None:
        url = httpx.URL(path)
        if (not path.startswith("/api/") or url.scheme or url.host
                or "\\" in path or any(ord(char) < 32 for char in path)
                or not httpx.URL(DEFAULT_BASE_URL).join(path).path.startswith("/api/")):
            raise MashovRequestError("Expected a relative Mashov API path.")
        if "follow_redirects" in options or "auth" in options:
            raise MashovRequestError("Request cannot override transport authentication or redirect policy.")

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

        self._validate_request(path, kwargs)
        try:
            await self.ensure_logged_in()
        except MashovLoginError as e:

            raise
            
        assert self._session is not None

        final_headers: Dict[str, str] = {}
        if headers:
            final_headers.update(headers)

        final_headers["X-Csrf-Token"] = self._session.csrf_header_token

        # HTTPX selects cookies for the destination and path.

        try:
            resp = await self._http.request(method, path, headers=final_headers, **kwargs)

        except httpx.TimeoutException:

            raise MashovRequestError("Mashov request timed out") from None
        except httpx.RequestError:

            raise MashovRequestError("Mashov request failed") from None

        if not resp.is_success:

            raise MashovRequestError(f"Mashov request failed ({resp.status_code})")

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
        self._validate_request(path, kwargs)

        final_headers: Dict[str, str] = {}
        if headers:
            final_headers.update(headers)

        try:
            resp = await self._http.request(
                method,
                path,
                headers=final_headers,
                **kwargs,
            )

        except httpx.TimeoutException:

            raise MashovRequestError("Mashov request timed out") from None
        except httpx.RequestError:

            raise MashovRequestError("Mashov request failed") from None

        if not resp.is_success:

            raise MashovRequestError(
                f"Mashov request failed ({resp.status_code})"
            )

        return resp

    # ---- Example endpoint wrapper ----
    async def get_grades(self, student_id: str) -> Any:
        """Get grades for a specific student."""

        resp = await self.request("GET", f"/api/students/{student_id}/grades")
        data = resp.json()

        return data

    async def get_schools(self) -> Any:
        """Get list of available schools (public endpoint)."""
        logger.info("Fetching schools list")
        resp = await self.public_request("GET", "/api/schools")
        data = resp.json()
        logger.info("Schools list fetched successfully")
        return data

    async def get_conversations(
        self,
        *,
        skip: int = 0,
        take: int = 20,
    ) -> Any:
        """Get mail inbox conversations."""

        resp = await self.request(
            "GET",
            "/api/mail/inbox/conversations",
            params={
                "skip": skip,
                "take": take,
            },
        )
        data = resp.json()

        return data
    
    async def get_timetable(self, student_id: str) -> Any:
        """
        Get timetable for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """

        path = f"/api/students/{student_id}/timetable"

        resp = await self.request("GET", path)
        data = resp.json()

        return data

    async def get_homework(self, student_id: str) -> Any:
        """
        Get homework for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """

        path = f"/api/students/{student_id}/homework"

        resp = await self.request("GET", path)
        data = resp.json()

        return data

    async def get_behavior(self, student_id: str) -> Any:
        """
        Get behavior/discipline records for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """

        path = f"/api/students/{student_id}/behave"

        resp = await self.request("GET", path)
        data = resp.json()

        return data
