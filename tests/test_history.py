
import unittest
from unittest.mock import AsyncMock, patch

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


class TestAPIHistory(unittest.TestCase):

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
    def test_api_request_is_saved(
        self,
        mock_send_request,
        mock_ai_diagnosis
    ):
        # Mock API response
        mock_send_request.return_value = {
            "status_code": 200,
            "response_time_ms": 250.0,
            "headers": {
                "content-type": "application/json",
                "x-content-type-options": "nosniff"
            },
            "body": '{"message": "Success"}'
        }

        mock_ai_diagnosis.return_value = "API is working correctly."

        # Send request to API Doctor
        response = self.client.post(
            "/api/test",
            json={
                "url": "https://example.com/api",
                "method": "GET"
            }
        )

        # Check HTTP response
        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertTrue(result["success"])
        self.assertIn("history_id", result)

        # Check whether the record exists in SQLite
        db = TestingSessionLocal()

        try:
            saved_record = db.query(APIHistory).filter_by(
                id=result["history_id"]
            ).first()

            self.assertIsNotNone(saved_record)
            self.assertEqual(
                saved_record.url,
                "https://example.com/api"
            )
            self.assertEqual(saved_record.method, "GET")
            self.assertEqual(saved_record.status_code, 200)
            self.assertEqual(saved_record.response_time_ms, 250.0)
            self.assertEqual(
                saved_record.ai_diagnosis,
                "API is working correctly."
            )

        finally:
            db.close()

        print("\nAPI history database test passed!")


if __name__ == "__main__":
    unittest.main()
