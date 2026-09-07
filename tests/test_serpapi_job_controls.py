import os
import unittest
from unittest.mock import patch

from dags.ingest import serpapi_get_jobs


class SerpApiJobControlsTest(unittest.TestCase):
    def test_dry_run_accepts_true_and_false(self):
        with patch.dict(os.environ, {"DRY_RUN": "true"}):
            self.assertTrue(serpapi_get_jobs._parse_dry_run())
        with patch.dict(os.environ, {"DRY_RUN": "FALSE"}):
            self.assertFalse(serpapi_get_jobs._parse_dry_run())

    def test_controls_reject_malformed_or_non_positive_values(self):
        for env_var, value in (
            ("DRY_RUN", "yes"),
            ("MAX_QUERIES", "0"),
            ("MAX_QUERIES", "two"),
            ("TEST_MAX_JOBS", "-1"),
        ):
            with self.subTest(env_var=env_var, value=value), patch.dict(
                os.environ, {env_var: value}
            ):
                parser = (
                    serpapi_get_jobs._parse_dry_run
                    if env_var == "DRY_RUN"
                    else lambda: serpapi_get_jobs._parse_optional_positive_int(env_var)
                )
                with self.assertRaises(ValueError):
                    parser()

    def test_test_max_jobs_overrides_row_max_jobs(self):
        row = {"query_id": 1, "q": "data engineer", "max_jobs": 250}
        self.assertEqual(
            serpapi_get_jobs._normalize_query_row(row, test_max_jobs=3)["max_jobs"], 3
        )

    def test_dry_run_validates_prerequisites_without_processing(self):
        query_rows = [{"query_id": 1, "q": "data engineer", "max_jobs": 250}]
        with patch.dict(
            os.environ,
            {
                "DRY_RUN": "true",
                "MAX_QUERIES": "1",
                "TEST_MAX_JOBS": "1",
                "GCS_BUCKET": "test-bucket",
                "BQ_PROJECT_ID": "test-project",
            },
            clear=True,
        ), patch.object(
            serpapi_get_jobs.secretmanager, "SecretManagerServiceClient"
        ) as secret_client, patch.object(
            serpapi_get_jobs, "_load_api_keys_from_secret", return_value=["key"]
        ) as load_keys, patch.object(
            serpapi_get_jobs.bigquery, "Client"
        ) as bq_client, patch.object(
            serpapi_get_jobs, "_fetch_query_versions", return_value=query_rows
        ) as fetch_rows, patch.object(
            serpapi_get_jobs.storage, "Client"
        ) as storage_client, patch.object(
            serpapi_get_jobs, "_iter_jobs_for_query"
        ) as fetch_jobs:
            serpapi_get_jobs.main()

        secret_client.assert_called_once_with()
        load_keys.assert_called_once()
        bq_client.assert_called_once_with(project="test-project")
        fetch_rows.assert_called_once()
        storage_client.assert_not_called()
        fetch_jobs.assert_not_called()


if __name__ == "__main__":
    unittest.main()
