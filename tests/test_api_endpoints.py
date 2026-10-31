
import unittest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models.history import APIHistory


# Create a separate temporary test database
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=test_engine)

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    @patch(
        "backend.routes.api_routes.generate_ai_diagnosis",
        new_callable=AsyncMock
    )
    @patch(
        "backend.routes.api_routes.send_api_request",
        new_callable=AsyncMock
    )
    def test_api_testing_endpoint(
        self,
        mock_send_request,
        mock_ai
    ):

        mock_send_request.return_value = {
            "status_code": 200,
            "response_time_ms": 200.0,
            "headers": {
                "content-type": "application/json",
                "x-content-type-options": "nosniff"
            },
            "body": '{"message": "Success"}'
        }

        mock_ai.return_value = "API is working correctly."

        response = self.client.post(
            "/api/test",
            json={
                "url": "https://example.com/api",
                "method": "GET"
            }
        )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertTrue(result["success"])
        self.assertIn("history_id", result)
        self.assertIn("analysis", result)

        # Verify that the history was saved
        db = TestingSessionLocal()

        try:
            record = db.query(APIHistory).filter_by(
                id=result["history_id"]
            ).first()

            self.assertIsNotNone(record)
            self.assertEqual(record.status_code, 200)

        finally:
            db.close()

    def test_invalid_api_request(self):

        response = self.client.post(
            "/api/test",
            json={
                "url": "https://example.com",
                "method": "INVALID"
            }
        )

        self.assertEqual(response.status_code, 422)

    def test_history_endpoint(self):

        db = TestingSessionLocal()

        db.add(
            APIHistory(
                url="https://example.com",
                method="GET",
                status_code=200,
                response_time_ms=150.0,
                health="Healthy",
                health_score=95,
                json_valid=True,
                issues=[],
                suggestions=[],
                ai_diagnosis="API is working correctly."
            )
        )

        db.commit()
        db.close()

        response = self.client.get("/api/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_history_not_found(self):

        response = self.client.get("/api/history/999")

        self.assertEqual(response.status_code, 404)

    def test_json_comparison_endpoint(self):

        response = self.client.post(
            "/api/compare",
            json={
                "response_a": {"name": "Arya"},
                "response_b": {"name": "Arya"}
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("comparison", response.json())

    @patch(
        "backend.routes.api_routes.generate_code_fix",
        new_callable=AsyncMock
    )
    def test_code_fix_endpoint(self, mock_code_fix):

        mock_code_fix.return_value = (
            "Problem explanation and corrected Python code."
        )

        response = self.client.post(
            "/api/generate-fix",
            json={
                "analysis": {
                    "status_code": 404,
                    "response_time_ms": 200,
                    "json_valid": True,
                    "issues": ["Resource not found"],
                    "suggestions": ["Check the endpoint"]
                },
                "language": "Python"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn("code_fix", response.json())


if __name__ == "__main__":
    unittest.main()
