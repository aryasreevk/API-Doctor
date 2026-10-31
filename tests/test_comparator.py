
import unittest

from backend.services.response_comparator import compare_json


class TestJSONComparator(unittest.TestCase):

    def test_added_field(self):
        response_a = {"name": "Arya"}
        response_b = {
            "name": "Arya",
            "email": "arya@example.com"
        }

        result = compare_json(response_a, response_b)

        self.assertFalse(result["identical"])
        self.assertTrue(result["added"])

    def test_missing_field(self):
        response_a = {
            "name": "Arya",
            "age": 21
        }
        response_b = {"name": "Arya"}

        result = compare_json(response_a, response_b)

        self.assertFalse(result["identical"])
        self.assertTrue(result["missing"])

    def test_changed_value(self):
        response_a = {"name": "Arya"}
        response_b = {"name": "Anu"}

        result = compare_json(response_a, response_b)

        self.assertFalse(result["identical"])
        self.assertTrue(result["changed"])

    def test_type_mismatch(self):
        response_a = {"age": 21}
        response_b = {"age": "21"}

        result = compare_json(response_a, response_b)

        self.assertFalse(result["identical"])
        self.assertTrue(result["type_mismatches"])

    def test_identical_responses(self):
        response_a = {
            "name": "Arya",
            "age": 21
        }
        response_b = {
            "name": "Arya",
            "age": 21
        }

        result = compare_json(response_a, response_b)

        self.assertTrue(result["identical"])


if __name__ == "__main__":
    unittest.main()
