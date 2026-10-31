
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.services.ai_diagnosis import generate_ai_diagnosis


class FakeAioClient:

    def __init__(self, response=None, error=None):
        self.models = SimpleNamespace(
            generate_content=AsyncMock(
                return_value=response
            )
        )

        if error:
            self.models.generate_content.side_effect = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def aclose(self):
        pass


class TestAIDiagnosis(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.analysis = {
            "status_code": 200,
            "response_time_ms": 250,
            "json_valid": True,
            "issues": [],
            "suggestions": []
        }

    @patch("backend.services.ai_diagnosis.API_KEY", "test-api-key")
    @patch("backend.services.ai_diagnosis.genai.Client")
    async def test_successful_diagnosis(self, mock_client):

        fake_aio = FakeAioClient(
            response=SimpleNamespace(
                text="The API is working correctly."
            )
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        result = await generate_ai_diagnosis(self.analysis)

        self.assertEqual(
            result,
            "The API is working correctly."
        )

        mock_client.assert_called_once()

    @patch("backend.services.ai_diagnosis.API_KEY", "test-api-key")
    @patch("backend.services.ai_diagnosis.genai.Client")
    async def test_empty_gemini_response(self, mock_client):

        fake_aio = FakeAioClient(
            response=SimpleNamespace(text=None)
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        with self.assertRaisesRegex(
            RuntimeError,
            "Empty Gemini response"
        ):
            await generate_ai_diagnosis(self.analysis)

    @patch("backend.services.ai_diagnosis.API_KEY", None)
    @patch("backend.services.ai_diagnosis.genai.Client")
    async def test_missing_api_key(self, mock_client):

        with self.assertRaisesRegex(
            ValueError,
            "Gemini API key is missing"
        ):
            await generate_ai_diagnosis(self.analysis)

        mock_client.assert_not_called()

    @patch("backend.services.ai_diagnosis.API_KEY", "test-api-key")
    @patch("backend.services.ai_diagnosis.genai.Client")
    async def test_gemini_service_error(self, mock_client):

        fake_aio = FakeAioClient(
            error=RuntimeError("Gemini service unavailable")
        )

        mock_client.return_value = SimpleNamespace(aio=fake_aio)

        with self.assertRaisesRegex(
            RuntimeError,
            "Gemini service unavailable"
        ):
            await generate_ai_diagnosis(self.analysis)


if __name__ == "__main__":
    unittest.main()
