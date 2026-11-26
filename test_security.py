import unittest
import httpx
from mashov import MashovClient, MashovLoginError, MashovRequestError
from mashov.models import MashovSession
from mashov.session import MashovSession as LegacySession


class SecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_origin_and_path_restrictions(self):
        for origin in ("http://web.mashov.info", "https://example.test", "https://web.mashov.info/api/", "https://user@web.mashov.info"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                MashovClient("fixture", "fixture", "123", base_url=origin)
        async with MashovClient("fixture", "fixture", "123") as client:
            for path in ("https://example.test/api/", "//example.test/api/", "/api/../outside", "/outside", "/api/\\outside"):
                with self.subTest(path=path), self.assertRaises(MashovRequestError):
                    await client.public_request("GET", path)
            for option in ({"auth": None}, {"follow_redirects": True}):
                with self.assertRaises(MashovRequestError):
                    await client.public_request("GET", "/api/schools", **option)

    async def test_redirects_and_errors_are_sanitized(self):
        for status in (307, 308, 400):
            calls = []

            def respond(request):
                calls.append(request.url.host)
                return httpx.Response(status, headers={"location": "https://example.test/"}, text="sensitive-fixture-body")

            async with MashovClient("fixture", "fixture", "123") as client:
                await client._http.aclose()
                client._http = httpx.AsyncClient(base_url=client._base_url, transport=httpx.MockTransport(respond), follow_redirects=False)
                with self.assertRaises(MashovLoginError) as caught:
                    await client.login()
                self.assertNotIn("sensitive-fixture-body", str(caught.exception))
                self.assertEqual(calls, ["web.mashov.info"])

    async def test_session_repr_hides_tokens(self):
        session = MashovSession("secret-csrf", "secret-cookie", "https://web.mashov.info", "2027", "secret-auth", "secret-csrf-cookie")
        self.assertNotIn("secret", repr(session))
        async with httpx.AsyncClient(trust_env=False) as http:
            self.assertNotIn("secret", repr(LegacySession(http, "secret-auth", "secret-csrf")))
