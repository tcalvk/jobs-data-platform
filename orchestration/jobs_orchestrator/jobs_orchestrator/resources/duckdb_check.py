"""Reusable declarative DuckDB checks for newline-delimited JSON."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import BinaryIO, Iterable

import duckdb
from dagster import ConfigurableResource


MINIMUM_MAXIMUM_OBJECT_SIZE = 16 * 1024 * 1024


class DuckDBCheckExecutionError(RuntimeError):
    """The validator could not conclusively execute its checks."""


@dataclass(frozen=True)
class NotNullCheck:
    """Require a JSON path to exist and have a non-null JSON value."""

    name: str
    json_path: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    failed_row_count: int


@dataclass(frozen=True)
class DuckDBCheckResult:
    passed: bool
    row_count: int
    checks: tuple[CheckResult, ...]


def _existing_local_path(source: BinaryIO) -> str | None:
    try:
        path = os.fsdecode(os.fspath(source.name))
    except (AttributeError, TypeError, ValueError):
        return None
    return path if os.path.isfile(path) else None


class DuckDBCheckResource(ConfigurableResource):
    """Execute source-agnostic checks against a JSONL stream with DuckDB."""

    def run_checks(
        self, source: BinaryIO, checks: Iterable[NotNullCheck]
    ) -> DuckDBCheckResult:
        """Run checks against a local JSONL path, copying only non-file streams."""
        original_position: int | None = None
        temp_path: str | None = None
        connection: duckdb.DuckDBPyConnection | None = None
        result: DuckDBCheckResult | None = None
        execution_error: BaseException | None = None
        cleanup_errors: list[BaseException] = []

        try:
            check_definitions = tuple(checks)
            original_position = source.tell()
            local_path = _existing_local_path(source)
            if local_path is not None:
                source.flush()
            else:
                source.seek(0)
                with tempfile.NamedTemporaryFile(
                    mode="w+b", suffix=".jsonl", delete=False
                ) as temp:
                    temp_path = temp.name
                    shutil.copyfileobj(source, temp)
                    temp.flush()
                local_path = temp_path

            maximum_object_size = max(
                os.path.getsize(local_path),
                MINIMUM_MAXIMUM_OBJECT_SIZE,
            )

            aggregate_expressions = ["count(*)"]
            parameters: list[object] = []
            for check in check_definitions:
                aggregate_expressions.append(
                    "count(*) FILTER (WHERE json_type(json, ?) IS NULL "
                    "OR json_type(json, ?) = 'NULL')"
                )
                parameters.extend((check.json_path, check.json_path))

            query = f"""
                SELECT {", ".join(aggregate_expressions)}
                FROM read_json_objects(
                    ?,
                    format='newline_delimited',
                    maximum_object_size=?
                )
            """
            parameters.extend((local_path, maximum_object_size))

            connection = duckdb.connect(database=":memory:")
            aggregate_row = connection.execute(query, parameters).fetchone()
            if aggregate_row is None:
                raise RuntimeError("DuckDB did not return a validation aggregate row.")

            check_results = tuple(
                CheckResult(check.name, int(aggregate_row[index]))
                for index, check in enumerate(check_definitions, start=1)
            )
            result = DuckDBCheckResult(
                passed=all(check.failed_row_count == 0 for check in check_results),
                row_count=int(aggregate_row[0]),
                checks=check_results,
            )
        except Exception as exc:
            execution_error = exc
        finally:
            try:
                if connection is not None:
                    connection.close()
            except Exception as exc:
                cleanup_errors.append(exc)
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    cleanup_errors.append(exc)
            if original_position is not None:
                try:
                    source.seek(original_position)
                except Exception as exc:
                    cleanup_errors.append(exc)

        cause = execution_error or (cleanup_errors[0] if cleanup_errors else None)
        if cause is not None:
            raise DuckDBCheckExecutionError(
                "DuckDB validation could not be completed conclusively."
            ) from cause
        if result is None:
            raise DuckDBCheckExecutionError("DuckDB validation produced no result.")
        return result
