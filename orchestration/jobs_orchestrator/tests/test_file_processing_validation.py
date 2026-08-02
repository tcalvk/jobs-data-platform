import io
import unittest

from jobs_orchestrator.assets.serpapi_load_jobs.file_processing import (
    InputValidationError,
    _parsed_records,
)


class ExistingStructuralValidationTests(unittest.TestCase):
    def test_malformed_json_keeps_invalid_json_category(self):
        with self.assertRaises(InputValidationError) as raised:
            list(_parsed_records(io.BytesIO(b'{"broken":}\n')))

        self.assertEqual(raised.exception.category, "invalid_json")

    def test_invalid_utf8_keeps_invalid_utf8_category(self):
        with self.assertRaises(InputValidationError) as raised:
            list(_parsed_records(io.BytesIO(b'{"value":"\xff"}\n')))

        self.assertEqual(raised.exception.category, "invalid_utf8")


if __name__ == "__main__":
    unittest.main()
