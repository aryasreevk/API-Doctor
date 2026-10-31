
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.services.code_fix_generator import generate_code_fix


class FakeAioClient:

    def __init__(self, response=None, error=None):
        self.models = SimpleNamespace(
            generate_content=AsyncMock(return_value=response)
        )

        if error:
            self.models.generate_content.side_effect = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class TestCodeFixGenerator(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.analysis = {
            "status_code": 404,
            "response_time_ms": 250,
            "json_valid": True,
            "issues": ["Resource not found"],
            "suggestions": ["Check the API endpoint"]
        }

    @patch("backend.services.code_fix_generator.API_KEY", "test-api-key")
    @patch("backend.services.code_fix_generator.genai.Client")
    async def test_successful_code_generation(self, mock_client):

        fake_aio = FakeAioClient(
            response=SimpleNamespace(
                text="Corrected Python code example"
            )
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        result = await generate_code_fix(
            self.analysis,
            "Python"
        )

        self.assertEqual(
            result,
            "Corrected Python code example"
        )

        mock_client.assert_called_once()

    async def test_unsupported_language(self):

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported programming language"
        ):
            await generate_code_fix(
                self.analysis,
                "Ruby"
            )

    @patch("backend.services.code_fix_generator.API_KEY", "test-api-key")
    @patch("backend.services.code_fix_generator.genai.Client")
    async def test_empty_gemini_response(self, mock_client):

        fake_aio = FakeAioClient(
            response=SimpleNamespace(text=None)
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        with self.assertRaisesRegex(
            RuntimeError,
            "Gemini returned an empty response"
        ):
            await generate_code_fix(
                self.analysis,
                "Python"
            )

    @patch("backend.services.code_fix_generator.API_KEY", "test-api-key")
    @patch("backend.services.code_fix_generator.genai.Client")
    async def test_gemini_service_failure(self, mock_client):

        fake_aio = FakeAioClient(
            error=RuntimeError("Gemini service unavailable")
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        with self.assertRaisesRegex(
            RuntimeError,
            "Gemini service unavailable"
        ):
            await generate_code_fix(
                self.analysis,
                "JavaScript"
            )


if __name__ == "__main__":
    unittest.main()
