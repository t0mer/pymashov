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
        logger.info(f"Initializing MashovClient for user: {username}, semel: {semel}, year: {year}")
        self._username = username
        self._password = password
        self._semel = semel
        self._year = str(year)
        self._base_url = base_url.rstrip("/")
        self._auto_login = auto_login

        try:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
                follow_redirects=True,
            )
            logger.debug(f"HTTP client created with timeout={timeout}s")
        except Exception as e:
            logger.error(f"Failed to create HTTP client: {e}")
            raise

        self._session: Optional[MashovSession] = None

    async def close(self) -> None:
        """Close the HTTP client connection."""
        try:
            logger.debug("Closing HTTP client connection")
            await self._http.aclose()
            logger.info("HTTP client connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}")
            raise

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
        logger.info(f"Attempting to login as user: {self._username} (semel: {self._semel}, year: {self._year})")
        
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
            logger.debug(f"Login request completed with status code: {resp.status_code}")
        except httpx.TimeoutException as e:
            logger.error(f"Login request timed out: {e}")
            raise MashovLoginError(f"Login request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Login request failed: {e}")
            raise MashovLoginError(f"Login request failed: {e}") from e

        if resp.status_code >= 400:
            logger.error(f"Login failed with status {resp.status_code}: {resp.text}")
            raise MashovLoginError(f"Login failed ({resp.status_code}): {resp.text}")

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
        logger.info(f"Login successful for user: {self._username}")
        logger.debug(f"Session established with CSRF token and cookies")
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
        logger.debug(f"Making {method} request to {path}")
        
        try:
            await self.ensure_logged_in()
        except MashovLoginError as e:
            logger.error(f"Failed to ensure login before request: {e}")
            raise
            
        assert self._session is not None

        final_headers: Dict[str, str] = {}
        if headers:
            final_headers.update(headers)

        final_headers["X-Csrf-Token"] = self._session.csrf_header_token

        # Optional: you can rely on the cookie jar, but you asked to attach it explicitly.
        final_headers["Cookie"] = self._session.cookie_header

        try:
            resp = await self._http.request(method, path, headers=final_headers, **kwargs)
            logger.debug(f"{method} {path} completed with status {resp.status_code}")
        except httpx.TimeoutException as e:
            logger.error(f"{method} {path} timed out: {e}")
            raise MashovRequestError(f"{method} {path} timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"{method} {path} request error: {e}")
            raise MashovRequestError(f"{method} {path} request error: {e}") from e

        if resp.status_code >= 400:
            logger.error(f"{method} {path} failed with status {resp.status_code}: {resp.text}")
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
        logger.debug(f"Making public {method} request to {path}")
        
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
            logger.debug(f"Public {method} {path} completed with status {resp.status_code}")
        except httpx.TimeoutException as e:
            logger.error(f"Public {method} {path} timed out: {e}")
            raise MashovRequestError(f"{method} {path} timed out: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"Public {method} {path} request error: {e}")
            raise MashovRequestError(f"{method} {path} request error: {e}") from e

        if resp.status_code >= 400:
            logger.error(f"Public {method} {path} failed with status {resp.status_code}: {resp.text}")
            raise MashovRequestError(
                f"{method} {path} failed ({resp.status_code}): {resp.text}"
            )

        return resp

    # ---- Example endpoint wrapper ----
    async def get_grades(self, student_id: str) -> Any:
        """Get grades for a specific student."""
        logger.info(f"Fetching grades for student: {student_id}")
        try:
            resp = await self.request("GET", f"/api/students/{student_id}/grades")
            data = resp.json()
            logger.info(f"Grades fetched successfully for student: {student_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to get grades for student {student_id}: {e}")
            raise

    async def get_schools(self) -> Any:
        """Get list of available schools (public endpoint)."""
        logger.info("Fetching schools list")
        try:
            resp = await self.public_request("GET", "/api/schools")
            data = resp.json()
            logger.info("Schools list fetched successfully")
            return data
        except Exception as e:
            logger.error(f"Failed to get schools list: {e}")
            raise

    async def get_conversations(
        self,
        *,
        skip: int = 0,
        take: int = 20,
    ) -> Any:
        """Get mail inbox conversations."""
        logger.info(f"Fetching conversations (skip={skip}, take={take})")
        try:
            resp = await self.request(
                "GET",
                "/api/mail/inbox/conversations",
                params={
                    "skip": skip,
                    "take": take,
                },
            )
            data = resp.json()
            logger.info(f"Conversations fetched successfully (skip={skip}, take={take})")
            return data
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            raise
    
    async def get_timetable(self, student_id: str) -> Any:
        """
        Get timetable for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        logger.info(f"Fetching timetable for student: {student_id}")
        path = f"/api/students/{student_id}/timetable"

        try:
            resp = await self.request("GET", path)
            data = resp.json()
            logger.info(f"Timetable fetched successfully for student: {student_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to get timetable for student {student_id}: {e}")
            raise
    

    async def get_homework(self, student_id: str) -> Any:
        """
        Get homework for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        logger.info(f"Fetching homework for student: {student_id}")
        path = f"/api/students/{student_id}/homework"

        try:
            resp = await self.request("GET", path)
            data = resp.json()
            logger.info(f"Homework fetched successfully for student: {student_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to get homework for student {student_id}: {e}")
            raise
    
    
    async def get_behavior(self, student_id: str) -> Any:
        """
        Get behavior/discipline records for a specific student.

        Auth required:
        - X-Csrf-Token
        - Cookies
        """
        logger.info(f"Fetching behavior records for student: {student_id}")
        path = f"/api/students/{student_id}/behave"

        try:
            resp = await self.request("GET", path)
            data = resp.json()
            logger.info(f"Behavior records fetched successfully for student: {student_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to get behavior for student {student_id}: {e}")
            raise