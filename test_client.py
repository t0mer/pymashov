import unittest
import httpx

from mashov.client import MashovClient
from mashov.exceptions import MashovLoginError


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_and_homework(self):
        def respond(request):
            self.assertEqual(request.url.host, "web.mashov.info")
            if request.url.path == "/api/login":
                return httpx.Response(200, headers={
                    "x-csrf-token": "fixture-csrf",
                    "set-cookie": "MashovAuthToken=fixture-cookie; Path=/api; Secure",
                })
            self.assertEqual(request.url.path, "/api/students/123/homework")
            self.assertEqual(request.headers["x-csrf-token"], "fixture-csrf")
            self.assertEqual(request.headers["cookie"], "MashovAuthToken=fixture-cookie")
            return httpx.Response(200, json=[{"description": "Fixture homework"}])

        async with MashovClient("fixture-user", "fixture-password", "123") as client:
            await client._http.aclose()
            client._http = httpx.AsyncClient(base_url=client._base_url, transport=httpx.MockTransport(respond))
            self.assertEqual(await client.get_homework("123"), [{"description": "Fixture homework"}])
            self.assertNotIn("fixture-csrf", repr(client.session))
            self.assertNotIn("fixture-cookie", repr(client.session))

    def test_production_transport_defaults(self):
        client = MashovClient("fixture-user", "fixture-password", "123")
        self.assertFalse(client._http.follow_redirects)
        self.assertFalse(client._http.trust_env)
        with self.assertRaises(ValueError):
            MashovClient("fixture-user", "fixture-password", "123", base_url="https://example.test")
