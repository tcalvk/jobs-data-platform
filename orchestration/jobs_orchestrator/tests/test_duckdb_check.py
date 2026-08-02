import copy
import io
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import jobs_orchestrator.resources.duckdb_check as duckdb_check
from jobs_orchestrator.resources.duckdb_check import (
    DuckDBCheckExecutionError,
    DuckDBCheckResource,
)
from jobs_orchestrator.assets.serpapi_load_jobs.serpapi_checks import SERPAPI_CHECKS


def _row(suffix: str = "1") -> dict:
    return {
        "created_at": "2026-07-29T12:00:00Z",
        "job_data": {
            "source_name": "serpapi",
            "query_id": f"query-{suffix}",
            "q": "data engineer",
            "location": "New York, NY",
            "fetched_at": "2026-07-29T12:00:00Z",
            "job": {"job_id": f"job-{suffix}"},
        },
        "query_version_id": f"query-{suffix}",
        "gcs_uri": "gs://test/incoming/jobs.jsonl",
    }


def _jsonl(*rows: dict) -> io.BytesIO:
    content = b"".join(
        json.dumps(row, separators=(",", ":")).encode("utf-8") + b"\n" for row in rows
    )
    return io.BytesIO(content)


def _field_parts(check) -> list[str]:
    return check.json_path.removeprefix("$.job_data.").split(".")


def _change_checked_value(row: dict, check, *, remove: bool) -> None:
    current = row["job_data"]
    parts = _field_parts(check)
    for part in parts[:-1]:
        current = current[part]
    if remove:
        current.pop(parts[-1])
    else:
        current[parts[-1]] = None


class DuckDBCheckTests(unittest.TestCase):
    def setUp(self):
        self.resource = DuckDBCheckResource()

    def test_serpapi_check_declarations_are_exact(self):
        self.assertEqual(
            [(check.name, check.json_path) for check in SERPAPI_CHECKS],
            [
                ("source_name_not_null", "$.job_data.source_name"),
                ("query_id_not_null", "$.job_data.query_id"),
                ("q_not_null", "$.job_data.q"),
                ("location_not_null", "$.job_data.location"),
                ("fetched_at_not_null", "$.job_data.fetched_at"),
                ("job_job_id_not_null", "$.job_data.job.job_id"),
            ],
        )

    def test_valid_multi_row_jsonl_passes(self):
        source = _jsonl(_row("1"), _row("2"))

        result = self.resource.run_checks(source, SERPAPI_CHECKS)

        self.assertTrue(result.passed)
        self.assertEqual(result.row_count, 2)
        self.assertTrue(all(check.failed_row_count == 0 for check in result.checks))

    def test_each_check_rejects_explicit_null_and_missing_path(self):
        for target_check in SERPAPI_CHECKS:
            for remove in (False, True):
                with self.subTest(check=target_check.name, value="missing" if remove else "null"):
                    invalid_row = copy.deepcopy(_row())
                    _change_checked_value(invalid_row, target_check, remove=remove)

                    result = self.resource.run_checks(_jsonl(invalid_row), SERPAPI_CHECKS)
                    failed_counts = {
                        check.name: check.failed_row_count for check in result.checks
                    }

                    self.assertFalse(result.passed)
                    self.assertEqual(result.row_count, 1)
                    self.assertEqual(failed_counts[target_check.name], 1)
                    self.assertEqual(sum(failed_counts.values()), 1)

    def test_multiple_failures_aggregate_by_check(self):
        first = copy.deepcopy(_row("1"))
        second = copy.deepcopy(_row("2"))
        first["job_data"].pop("source_name")
        first["job_data"]["q"] = None
        second["job_data"]["source_name"] = None
        second["job_data"].pop("location")

        result = self.resource.run_checks(_jsonl(first, second), SERPAPI_CHECKS)
        failed_counts = {check.name: check.failed_row_count for check in result.checks}

        self.assertFalse(result.passed)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(failed_counts["source_name_not_null"], 2)
        self.assertEqual(failed_counts["q_not_null"], 1)
        self.assertEqual(failed_counts["location_not_null"], 1)
        self.assertEqual(sum(failed_counts.values()), 4)

    def test_empty_strings_are_not_null(self):
        row = _row()
        for check in SERPAPI_CHECKS:
            current = row["job_data"]
            parts = _field_parts(check)
            for part in parts[:-1]:
                current = current[part]
            current[parts[-1]] = ""

        result = self.resource.run_checks(_jsonl(row), SERPAPI_CHECKS)

        self.assertTrue(result.passed)
        self.assertTrue(all(check.failed_row_count == 0 for check in result.checks))

    def test_in_memory_stream_position_is_restored(self):
        source = _jsonl(_row())
        source.seek(7)

        result = self.resource.run_checks(source, SERPAPI_CHECKS)

        self.assertTrue(result.passed)
        self.assertEqual(source.tell(), 7)

    def test_row_and_failure_counts_use_one_parameterized_select(self):
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = (2, 0, 0, 0, 0, 0, 0)

        with patch.object(duckdb_check.duckdb, "connect", return_value=connection):
            result = self.resource.run_checks(
                _jsonl(_row("1"), _row("2")), SERPAPI_CHECKS
            )

        self.assertTrue(result.passed)
        connection.execute.assert_called_once()
        query, parameters = connection.execute.call_args.args
        self.assertIn("SELECT count(*)", query)
        self.assertNotIn("CREATE TEMP TABLE", query)
        for check in SERPAPI_CHECKS:
            self.assertEqual(parameters.count(check.json_path), 2)

    def test_file_backed_large_record_uses_path_and_dynamic_object_size(self):
        source = tempfile.NamedTemporaryFile(mode="w+b", suffix=".jsonl", delete=False)
        try:
            row = _row()
            row["large_payload"] = "x" * (16 * 1024 * 1024)
            source.write(json.dumps(row, separators=(",", ":")).encode("utf-8") + b"\n")
            source.flush()
            source.seek(11)

            with patch.object(
                duckdb_check.tempfile,
                "NamedTemporaryFile",
                side_effect=AssertionError("file-backed input must not be copied"),
            ):
                result = self.resource.run_checks(source, SERPAPI_CHECKS)

            self.assertTrue(result.passed)
            self.assertEqual(source.tell(), 11)
        finally:
            source.close()
            os.unlink(source.name)

    def test_execution_error_closes_connection_removes_copy_and_restores_stream(self):
        source = _jsonl(_row())
        source.seek(9)
        created_paths = []
        real_named_temporary_file = tempfile.NamedTemporaryFile

        def tracked_temporary_file(*args, **kwargs):
            temporary_file = real_named_temporary_file(*args, **kwargs)
            created_paths.append(temporary_file.name)
            return temporary_file

        connection = MagicMock()
        connection.execute.side_effect = RuntimeError("simulated DuckDB failure")
        with (
            patch.object(
                duckdb_check.tempfile,
                "NamedTemporaryFile",
                side_effect=tracked_temporary_file,
            ),
            patch.object(duckdb_check.duckdb, "connect", return_value=connection),
        ):
            with self.assertRaises(DuckDBCheckExecutionError) as raised:
                self.resource.run_checks(source, SERPAPI_CHECKS)

        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        connection.close.assert_called_once_with()
        self.assertEqual(source.tell(), 9)
        self.assertTrue(created_paths)
        self.assertTrue(all(not os.path.exists(path) for path in created_paths))


if __name__ == "__main__":
    unittest.main()
