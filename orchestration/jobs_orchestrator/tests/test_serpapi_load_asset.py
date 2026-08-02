import io
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dagster import Failure, RetryRequested

import jobs_orchestrator.assets.serpapi_load_jobs.asset as asset_module
from jobs_orchestrator.assets.serpapi_load_jobs.asset import SerpapiLoadJobsConfig
from jobs_orchestrator.resources.duckdb_check import (
    CheckResult,
    DuckDBCheckExecutionError,
    DuckDBCheckResult,
)


class SerpapiLoadAssetTests(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(retry_number=0, log=MagicMock())
        self.source_blob = MagicMock()
        self.bucket = MagicMock()
        self.bucket.blob.return_value = self.source_blob
        self.bigquery_client = MagicMock()
        self.gcp = SimpleNamespace(
            bucket=lambda: self.bucket,
            bucket_name="test-bucket",
            normalized_incoming_prefix="serpapi/incoming",
            normalized_archive_prefix="serpapi/archive",
            normalized_reject_prefix="serpapi/reject",
            environment="test",
            raw_table_id="test-project.raw.serpapi_jobs",
            bigquery_client=self.bigquery_client,
        )
        self.config = SerpapiLoadJobsConfig(
            object_name="serpapi/incoming/jobs.jsonl",
            generation=123,
        )
        self.transformed = io.BytesIO(b'{"job_data":{}}\n')
        self.duckdb_check = MagicMock()

    def _invoke(self):
        return asset_module.serpapi_load_jobs.op.compute_fn.decorated_fn(
            self.context, self.config, self.gcp, self.duckdb_check
        )

    def test_failed_duckdb_result_rejects_before_bigquery_submission(self):
        failed_result = DuckDBCheckResult(
            passed=False,
            row_count=1,
            checks=(CheckResult("query_id_not_null", 1),),
        )
        rejected_blob = SimpleNamespace(generation=456)

        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(
                asset_module,
                "transform_jsonl_to_tempfile",
                return_value=(self.transformed, 1),
            ),
            patch.object(
                asset_module,
                "copy_then_delete_generation",
                return_value=rejected_blob,
            ) as move_generation,
            patch.object(asset_module, "close_and_remove_tempfile") as cleanup,
        ):
            self.duckdb_check.run_checks.return_value = failed_result
            with self.assertRaises(Failure) as raised:
                self._invoke()

        self.bigquery_client.load_table_from_file.assert_not_called()
        move_generation.assert_called_once_with(
            self.bucket,
            "serpapi/incoming/jobs.jsonl",
            123,
            "serpapi/reject/jobs.jsonl",
            reject_category="duckdb_check_failed",
        )
        cleanup.assert_called_once_with(self.transformed)
        self.assertIn("query_id_not_null=1", raised.exception.description)
        self.assertNotIn("job_data", raised.exception.description)

    def test_passing_validation_loads_bigquery_then_archives(self):
        passed_result = DuckDBCheckResult(passed=True, row_count=1, checks=())
        load_job = MagicMock(job_id="bq-job-1")
        events = []

        def validate(source, checks):
            events.append("validation")
            source.seek(5)
            return passed_result

        def submit_load(*args, **kwargs):
            self.assertEqual(args[0].tell(), 0)
            events.append("bigquery")
            return load_job

        def archive(*args, **kwargs):
            events.append("archive")
            return SimpleNamespace(generation=456)

        self.bigquery_client.load_table_from_file.side_effect = submit_load
        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(
                asset_module,
                "transform_jsonl_to_tempfile",
                return_value=(self.transformed, 1),
            ),
            patch.object(
                asset_module, "copy_then_delete_generation", side_effect=archive
            ) as move_generation,
            patch.object(asset_module, "close_and_remove_tempfile") as cleanup,
        ):
            self.duckdb_check.run_checks.side_effect = validate
            result = self._invoke()

        self.assertEqual(events, ["validation", "bigquery", "archive"])
        load_job.result.assert_called_once_with(
            timeout=asset_module.BIGQUERY_JOB_TIMEOUT_SECONDS
        )
        move_generation.assert_called_once_with(
            self.bucket,
            "serpapi/incoming/jobs.jsonl",
            123,
            "serpapi/archive/jobs.jsonl",
        )
        cleanup.assert_called_once_with(self.transformed)
        self.assertEqual(result.metadata["bigquery_job_id"], "bq-job-1")

    def test_duckdb_execution_error_retries_first_two_attempts_without_load_or_move(self):
        for retry_number in (0, 1):
            with self.subTest(retry_number=retry_number):
                self.context.retry_number = retry_number
                with (
                    patch.object(asset_module, "ensure_prefix_markers"),
                    patch.object(
                        asset_module,
                        "transform_jsonl_to_tempfile",
                        return_value=(self.transformed, 1),
                    ),
                    patch.object(
                        asset_module, "copy_then_delete_generation"
                    ) as move_generation,
                    patch.object(asset_module, "close_and_remove_tempfile") as cleanup,
                    patch.object(asset_module, "_retry_delay", return_value=0.0),
                ):
                    self.duckdb_check.run_checks.side_effect = (
                        DuckDBCheckExecutionError("inconclusive")
                    )
                    with self.assertRaises(RetryRequested):
                        self._invoke()

                self.bigquery_client.load_table_from_file.assert_not_called()
                move_generation.assert_not_called()
                cleanup.assert_called_once_with(self.transformed)

    def test_final_duckdb_execution_error_leaves_source_incoming(self):
        self.context.retry_number = 2
        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(
                asset_module,
                "transform_jsonl_to_tempfile",
                return_value=(self.transformed, 1),
            ),
            patch.object(asset_module, "copy_then_delete_generation") as move_generation,
            patch.object(asset_module, "close_and_remove_tempfile") as cleanup,
        ):
            self.duckdb_check.run_checks.side_effect = DuckDBCheckExecutionError(
                "inconclusive"
            )
            with self.assertRaises(Failure) as raised:
                self._invoke()

        self.bigquery_client.load_table_from_file.assert_not_called()
        move_generation.assert_not_called()
        cleanup.assert_called_once_with(self.transformed)
        self.assertIn("remains incoming", raised.exception.description)
        self.assertIn("not submitted to BigQuery", raised.exception.description)


if __name__ == "__main__":
    unittest.main()
