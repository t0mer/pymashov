import unittest
import os
from unittest.mock import patch
import httpx
from mashov import MashovClient, MashovLoginError


class ChildrenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    async def test_children_and_homework_use_guid(self):
        guid = "11111111-1111-4111-8111-111111111111"
        calls = []

        def respond(request):
            calls.append(request.url.path)
            if request.url.path == "/api/login":
                return httpx.Response(200, headers={
                    "x-csrf-token": "synthetic-csrf",
                    "set-cookie": "MashovAuthToken=synthetic-cookie; Path=/api; Secure",
                }, json={"accessToken": {"children": [
                    {"childGuid": guid, "privateName": "Synthetic", "familyName": "Child"},
                ]}})
            self.assertEqual(request.url.path, "/api/students/" + guid + "/homework")
            return httpx.Response(200, json=[])

        async with MashovClient("fixture", "fixture", "123") as client:
            await client._http.aclose()
            client._http = httpx.AsyncClient(base_url=client._base_url, transport=httpx.MockTransport(respond))
            children = await client.get_children()
            self.assertEqual(len(children), 1)
            self.assertEqual(children[0].private_name, "Synthetic")
            self.assertNotIn(guid, repr(children))
            self.assertNotIn("Synthetic", repr(children))
            self.assertEqual(await client.get_homework(children[0].child_guid), [])
            self.assertEqual(await client.get_children(), children)
            self.assertEqual(calls.count("/api/login"), 1)

    async def test_empty_children_and_malformed_guid(self):
        payloads = [{"accessToken": {}}, {"accessToken": {"children": [
            {"childGuid": "invalid", "privateName": "Synthetic"},
        ]}}]

        def respond(request):
            return httpx.Response(200, headers={
                "x-csrf-token": "synthetic-csrf",
                "set-cookie": "MashovAuthToken=synthetic-cookie; Path=/api; Secure",
            }, json=payloads.pop(0))

        async with MashovClient("fixture", "fixture", "123") as client:
            await client._http.aclose()
            client._http = httpx.AsyncClient(base_url=client._base_url, transport=httpx.MockTransport(respond))
            self.assertEqual(await client.get_children(), ())
            with self.assertRaisesRegex(MashovLoginError, "Invalid children"):
                await client.login()
