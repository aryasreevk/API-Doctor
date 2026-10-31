
import unittest
from unittest.mock import patch

from backend.services.request_engine import send_api_request


class FakeContent:

    def __init__(self, body):
        self.body = body

    async def iter_chunked(self, size):
        yield self.body


class FakeResponse:

    def __init__(self, body, status=200):
        self.status = status
        self.headers = {
            "content-type": "application/json"
        }
        self.content = FakeContent(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class FakeSession:

    def __init__(self, response):
        self.response = response
        self.request_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    def request(self, **kwargs):
        self.request_kwargs = kwargs
        return self.response


class TestAPIRequestEngine(unittest.IsolatedAsyncioTestCase):

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_invalid_url_scheme(self, mock_session):

        with self.assertRaisesRegex(
            ValueError,
            "Only HTTP and HTTPS URLs are allowed"
        ):
            await send_api_request("ftp://example.com")

        mock_session.assert_not_called()

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_missing_hostname(self, mock_session):

        with self.assertRaisesRegex(
            ValueError,
            "Invalid URL"
        ):
            await send_api_request("https:///")

        mock_session.assert_not_called()

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_credentials_in_url_rejected(self, mock_session):

        with self.assertRaisesRegex(
            ValueError,
            "URLs containing credentials are not allowed"
        ):
            await send_api_request(
                "https://user:password@example.com"
            )

        mock_session.assert_not_called()

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_successful_api_request(self, mock_session):

        fake_response = FakeResponse(
            b'{"message": "Success"}'
        )

        fake_session = FakeSession(fake_response)
        mock_session.return_value = fake_session

        result = await send_api_request(
            "https://example.com"
        )

        self.assertEqual(result["status_code"], 200)
        self.assertEqual(
            result["body"],
            '{"message": "Success"}'
        )
        self.assertIn("response_time_ms", result)
        self.assertIn("headers", result)

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_response_size_limit(self, mock_session):

        fake_response = FakeResponse(
            b"a" * 1_000_001
        )

        fake_session = FakeSession(fake_response)
        mock_session.return_value = fake_session

        with self.assertRaisesRegex(
            ValueError,
            "Response exceeds 1 MB limit"
        ):
            await send_api_request(
                "https://example.com"
            )

    @patch("backend.services.request_engine.aiohttp.ClientSession")
    async def test_redirects_disabled(self, mock_session):

        fake_response = FakeResponse(
            b"Redirect response",
            status=302
        )

        fake_session = FakeSession(fake_response)
        mock_session.return_value = fake_session

        result = await send_api_request(
            "https://example.com"
        )

        self.assertEqual(result["status_code"], 302)

        self.assertFalse(
            fake_session.request_kwargs["allow_redirects"]
        )


if __name__ == "__main__":
    unittest.main()
