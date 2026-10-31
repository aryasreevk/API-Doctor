
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models.history import APIHistory


# Separate temporary database for testing
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


class TestHistoryRetrieval(unittest.TestCase):

    def setUp(self):
        Base.metadata.create_all(bind=test_engine)

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Insert sample history records
        db = TestingSessionLocal()

        records = [
            APIHistory(
                url="https://example.com/api/1",
                method="GET",
                status_code=200,
                response_time_ms=150.0,
                health="Healthy",
                health_score=95,
                json_valid=True,
                issues=[],
                suggestions=[],
                ai_diagnosis="API is working correctly."
            ),
            APIHistory(
                url="https://example.com/api/2",
                method="POST",
                status_code=404,
                response_time_ms=300.0,
                health="Critical",
                health_score=40,
                json_valid=True,
                issues=["Resource not found"],
                suggestions=["Check the endpoint"],
                ai_diagnosis="The requested resource was not found."
            ),
            APIHistory(
                url="https://example.com/api/3",
                method="GET",
                status_code=500,
                response_time_ms=500.0,
                health="Critical",
                health_score=20,
                json_valid=False,
                issues=["Server error"],
                suggestions=["Check the server"],
                ai_diagnosis="The server returned an error."
            )
        ]

        db.add_all(records)
        db.commit()
        db.close()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)

    def test_get_all_history(self):

        response = self.client.get("/api/history")

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["history"]), 3)

    def test_get_history_by_id(self):

        response = self.client.get("/api/history/1")

        self.assertEqual(response.status_code, 200)

        result = response.json()["history"]

        self.assertEqual(result["id"], 1)
        self.assertEqual(
            result["url"],
            "https://example.com/api/1"
        )
        self.assertEqual(result["status_code"], 200)

    def test_nonexistent_history_id(self):

        response = self.client.get("/api/history/999")

        self.assertEqual(response.status_code, 404)

    def test_history_limit(self):

        response = self.client.get(
            "/api/history?limit=2"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_invalid_history_limit(self):

        response = self.client.get(
            "/api/history?limit=150"
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
