import io
import os
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
        self.context = SimpleNamespace(
            retry_number=0, log=MagicMock(), run_id="dagster-run-abc"
        )
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
        self.slack_notifications = MagicMock()

    def _invoke(self):
        return asset_module.serpapi_load_jobs.op.compute_fn.decorated_fn(
            self.context,
            self.config,
            self.gcp,
            self.duckdb_check,
            self.slack_notifications,
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
        self.slack_notifications.send_message.assert_called_once()
        message = self.slack_notifications.send_message.call_args.args[0]
        self.assertIn("*Environment:* test", message)
        self.assertIn("*Asset:* serpapi_load_jobs", message)
        self.assertIn("*Rejected filename:* jobs.jsonl", message)
        self.assertIn(
            "*Rejected object path:* serpapi/reject/jobs.jsonl", message
        )
        self.assertIn(
            "*Rejected GCS URI:* gs://test-bucket/serpapi/reject/jobs.jsonl",
            message,
        )
        self.assertIn("*Rejection category:* duckdb_check_failed", message)
        self.assertIn("*Source generation:* 123", message)
        self.assertIn("*Dagster run ID:* dagster-run-abc", message)

    def test_notification_follows_copy_metadata_patch_and_source_delete(self):
        events = []
        destination = MagicMock()
        destination.generation = 456
        destination.metadata = {}
        destination.metageneration = 7

        self.source_blob.reload.side_effect = lambda: events.append("source_reload")
        self.bucket.copy_blob.side_effect = lambda *args, **kwargs: (
            events.append("copy") or destination
        )
        destination.reload.side_effect = lambda: events.append("destination_reload")
        destination.patch.side_effect = lambda **kwargs: events.append("metadata_patch")
        self.source_blob.delete.side_effect = lambda **kwargs: events.append("source_delete")

        self.slack_notifications.send_message.side_effect = lambda _message: events.append(
            "notification"
        )
        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(Failure):
                self._invoke()

        self.assertEqual(
            events,
            [
                "source_reload",
                "copy",
                "destination_reload",
                "metadata_patch",
                "source_delete",
                "notification",
            ],
        )
        self.assertEqual(
            destination.metadata["dagster_reject_category"], "unsupported_extension"
        )
        destination.patch.assert_called_once_with(if_metageneration_match=7)
        self.source_blob.delete.assert_called_once_with(if_generation_match=123)

    def test_source_delete_failure_after_metadata_patch_does_not_notify(self):
        destination = MagicMock(
            generation=456,
            metadata={},
            metageneration=7,
        )
        self.bucket.copy_blob.return_value = destination
        delete_error = RuntimeError("private storage failure")
        self.source_blob.delete.side_effect = delete_error

        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                self._invoke()

        self.assertIs(raised.exception, delete_error)
        destination.patch.assert_called_once_with(if_metageneration_match=7)
        self.source_blob.delete.assert_called_once_with(if_generation_match=123)
        self.slack_notifications.send_message.assert_not_called()

    def test_valid_configured_run_url_is_encoded_and_included(self):
        self.context.run_id = "run/id with spaces?"
        with (
            patch.dict(
                os.environ,
                {"DAGSTER_WEB_URL": "https://dagster.example/base"},
            ),
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(
                asset_module,
                "copy_then_delete_generation",
                return_value=SimpleNamespace(generation=456),
            ),
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(Failure):
                self._invoke()

        message = self.slack_notifications.send_message.call_args.args[0]
        self.assertIn(
            "*Dagster run:* https://dagster.example/base/runs/"
            "run%2Fid%20with%20spaces%3F",
            message,
        )

    def test_malformed_run_url_is_omitted_without_suppressing_notification(self):
        with (
            patch.dict(os.environ, {"DAGSTER_WEB_URL": "http://[::1"}),
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(
                asset_module,
                "copy_then_delete_generation",
                return_value=SimpleNamespace(generation=456),
            ),
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(Failure):
                self._invoke()

        self.slack_notifications.send_message.assert_called_once()
        message = self.slack_notifications.send_message.call_args.args[0]
        self.assertNotIn("*Dagster run:*", message)
        self.assertIn("*Dagster run ID:* dagster-run-abc", message)

    def test_unsafe_or_invalid_run_urls_are_omitted(self):
        invalid_urls = (
            "http://[::1",
            "https://bad host.example",
            "https://dagster.example:not-a-port",
            "https://dagster.example:99999",
            "https://dagster.example:",
            "https://user:password@dagster.example",
            "https://dagster.example/path?query=value",
            "https://dagster.example/path?",
            "https://dagster.example/path#fragment",
            "https://dagster.example/path#",
            "ftp://dagster.example",
            "https://-invalid.example",
            "https://999.999.999.999",
            "https://dagster.example/bad%escape",
            "https:\\dagster.example",
        )
        for base_url in invalid_urls:
            with self.subTest(base_url=base_url), patch.dict(
                os.environ, {"DAGSTER_WEB_URL": base_url}
            ):
                self.assertIsNone(asset_module._configured_run_url("run-id"))

    def test_http_run_url_is_allowed_only_for_localhost_and_loopback(self):
        allowed_urls = (
            "http://localhost:3000",
            "http://localhost.:3000/dagster",
            "http://127.0.0.1:3000",
            "http://127.42.10.9",
            "http://[::1]:3000",
        )
        for base_url in allowed_urls:
            with self.subTest(base_url=base_url), patch.dict(
                os.environ, {"DAGSTER_WEB_URL": base_url}
            ):
                self.assertEqual(
                    asset_module._configured_run_url("run/id"),
                    f"{base_url}/runs/run%2Fid",
                )

        disallowed_urls = (
            "http://dagster.example",
            "http://192.168.1.10:3000",
            "http://0.0.0.0:3000",
            "http://[::2]:3000",
        )
        for base_url in disallowed_urls:
            with self.subTest(base_url=base_url), patch.dict(
                os.environ, {"DAGSTER_WEB_URL": base_url}
            ):
                self.assertIsNone(asset_module._configured_run_url("run-id"))

    def test_reject_move_failure_does_not_notify(self):
        reject_error = RuntimeError("storage unavailable")
        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(
                asset_module,
                "copy_then_delete_generation",
                side_effect=reject_error,
            ) as move_generation,
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(RuntimeError) as raised:
                self._invoke()

        self.assertIs(raised.exception, reject_error)
        move_generation.assert_called_once()
        self.slack_notifications.send_message.assert_not_called()

    def test_slack_failure_does_not_mask_original_rejection_or_move_again(self):
        self.slack_notifications.send_message.side_effect = RuntimeError(
            "webhook secret and payload must not be logged"
        )
        with (
            patch.object(asset_module, "ensure_prefix_markers"),
            patch.object(asset_module, "is_supported_jsonl", return_value=False),
            patch.object(
                asset_module,
                "copy_then_delete_generation",
                return_value=SimpleNamespace(generation=456),
            ) as move_generation,
            patch.object(asset_module, "close_and_remove_tempfile"),
        ):
            with self.assertRaises(Failure) as raised:
                self._invoke()

        self.assertIn("Only lowercase .jsonl files are supported", raised.exception.description)
        move_generation.assert_called_once()
        self.slack_notifications.send_message.assert_called_once()
        error_log_args = self.context.log.error.call_args_list[-1].args
        self.assertIn("completed file rejection is unchanged", error_log_args[0])
        self.assertNotIn(
            "webhook secret and payload", " ".join(map(str, error_log_args))
        )

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
        self.slack_notifications.send_message.assert_not_called()

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
