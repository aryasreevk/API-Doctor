
import unittest
import asyncio
import socket
from unittest.mock import patch, MagicMock, AsyncMock

import aiohttp

from backend.services.request_engine import (
    send_api_request,
    SafeDNSResolver
)


class TestAPIRequestErrors(unittest.IsolatedAsyncioTestCase):

    async def test_dns_resolution_failure(self):

        resolver = SafeDNSResolver()

        with patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            side_effect=socket.gaierror()
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Unable to resolve the hostname"
            ):
                await resolver.resolve(
                    "unknown.example",
                    443
                )

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_connection_error(self, mock_session):

        fake_session = MagicMock()

        fake_session.__aenter__ = AsyncMock(
            return_value=fake_session
        )
        fake_session.__aexit__ = AsyncMock(
            return_value=False
        )

        fake_session.request.side_effect = (
            aiohttp.ClientConnectionError("Connection failed")
        )

        mock_session.return_value = fake_session

        with self.assertRaises(aiohttp.ClientConnectionError):
            await send_api_request("https://example.com")

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_timeout_error(self, mock_session):

        fake_session = MagicMock()

        fake_session.__aenter__ = AsyncMock(
            return_value=fake_session
        )
        fake_session.__aexit__ = AsyncMock(
            return_value=False
        )

        fake_session.request.side_effect = asyncio.TimeoutError()

        mock_session.return_value = fake_session

        with self.assertRaises(asyncio.TimeoutError):
            await send_api_request("https://example.com")

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_http_server_error_response(self, mock_session):

        from tests.test_request_engine import (
            FakeSession,
            FakeResponse
        )

        fake_response = FakeResponse(
            b'{"error": "Internal Server Error"}',
            status=500
        )

        mock_session.return_value = FakeSession(fake_response)

        result = await send_api_request("https://example.com")

        self.assertEqual(result["status_code"], 500)
        self.assertIn("Internal Server Error", result["body"])


if __name__ == "__main__":
    unittest.main()
