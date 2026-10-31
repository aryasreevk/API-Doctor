
import unittest

from backend.services.analyzer import analyze_response


class TestAPIAnalyzer(unittest.TestCase):

    def test_successful_api_response(self):
        result = analyze_response(
            200,
            250.0,
            {
                "content-type": "application/json",
                "x-content-type-options": "nosniff"
            },
            '{"message": "Success"}'
        )

        self.assertEqual(result["status_code"], 200)
        self.assertTrue(result["json_valid"])
        self.assertGreaterEqual(result["health_score"], 0)
        self.assertLessEqual(result["health_score"], 100)

    def test_server_error_response(self):
        result = analyze_response(
            500,
            200.0,
            {"content-type": "application/json"},
            '{"error": "Internal Server Error"}'
        )

        self.assertEqual(result["status_code"], 500)
        self.assertLess(result["health_score"], 100)

    def test_invalid_json_response(self):
        result = analyze_response(
            200,
            200.0,
            {"content-type": "application/json"},
            "This is not valid JSON"
        )

        self.assertFalse(result["json_valid"])

    def test_slow_api_response(self):
        result = analyze_response(
            200,
            4000.0,
            {
                "content-type": "application/json",
                "x-content-type-options": "nosniff"
            },
            '{"message": "Slow response"}'
        )

        self.assertTrue(
            any("slow" in issue.lower()
                for issue in result["issues"])
        )


if __name__ == "__main__":
    unittest.main()
