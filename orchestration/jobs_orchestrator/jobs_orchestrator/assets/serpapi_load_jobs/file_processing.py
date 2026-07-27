"""Streaming validation and generation-safe GCS lifecycle helpers."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator

from google.api_core import exceptions as google_exceptions
from google.cloud import storage


TEMP_DIRECTORY = Path("/var/tmp/jobs-orchestrator")


class InputValidationError(ValueError):
    """A permanent error caused by the uploaded object itself."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


def incoming_relative_path(object_name: str, incoming_prefix: str) -> str:
    prefix = incoming_prefix.strip("/") + "/"
    if not object_name.startswith(prefix):
        raise InputValidationError("outside_incoming", "Object is not below the incoming prefix.")
    relative = object_name[len(prefix) :]
    if not relative:
        raise InputValidationError("directory_placeholder", "Incoming prefix marker is not a file.")
    return relative


def lifecycle_object_name(object_name: str, incoming_prefix: str, target_prefix: str) -> str:
    return f"{target_prefix.strip('/')}/{incoming_relative_path(object_name, incoming_prefix)}"


def is_directory_placeholder(blob: storage.Blob) -> bool:
    return blob.name.endswith("/")


def is_supported_jsonl(object_name: str) -> bool:
    return object_name.endswith(".jsonl")


def ensure_prefix_markers(bucket: storage.Bucket, *prefixes: str) -> None:
    """Create console-visible lifecycle markers, never an incoming marker."""
    for prefix in prefixes:
        marker = bucket.blob(prefix.strip("/") + "/")
        if not marker.exists():
            marker.upload_from_string(b"", content_type="application/x-directory")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant {value!r} is not allowed")


def build_bq_row(record: dict[str, Any], gcs_uri: str) -> dict[str, Any]:
    return {
        "created_at": record.get("fetched_at"),
        "job_data": record,
        "query_version_id": record.get("query_id"),
        "gcs_uri": gcs_uri,
    }


def _parsed_records(handle: BinaryIO) -> Iterator[dict[str, Any]]:
    for line_number, raw_line in enumerate(handle, start=1):
        if not raw_line.strip():
            continue
        try:
            text = raw_line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InputValidationError("invalid_utf8", f"Invalid UTF-8 on line {line_number}.") from exc
        try:
            value = json.loads(text, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise InputValidationError("invalid_json", f"Invalid JSON on line {line_number}.") from exc
        if not isinstance(value, dict):
            raise InputValidationError("non_object_json", f"JSON line {line_number} is not an object.")
        yield value


def transform_jsonl_to_tempfile(blob: storage.Blob, gcs_uri: str) -> tuple[BinaryIO, int]:
    """Validate all records while writing target JSONL without retaining source rows."""
    TEMP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    temp = tempfile.NamedTemporaryFile(mode="w+b", dir=TEMP_DIRECTORY, suffix=".jsonl", delete=False)
    count = 0
    try:
        with blob.open("rb") as source:
            for record in _parsed_records(source):
                row = build_bq_row(record, gcs_uri)
                temp.write(json.dumps(row, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n")
                count += 1
        if count == 0:
            raise InputValidationError("empty_file", "Object has no nonblank JSON records.")
        temp.flush()
        temp.seek(0)
        return temp, count
    except Exception:
        temp.close()
        os.unlink(temp.name)
        raise


def close_and_remove_tempfile(handle: BinaryIO | None) -> None:
    if handle is None:
        return
    name = handle.name
    handle.close()
    try:
        os.unlink(name)
    except FileNotFoundError:
        pass


def copy_then_delete_generation(
    bucket: storage.Bucket,
    source_name: str,
    generation: int,
    destination_name: str,
    reject_category: str | None = None,
) -> storage.Blob:
    """Copy an exact source generation, then delete only that same generation."""
    source = bucket.blob(source_name, generation=generation)
    source.reload()  # Fails stale runs before an overwrite can be copied.
    destination = bucket.copy_blob(
        source,
        bucket,
        new_name=destination_name,
        if_source_generation_match=generation,
    )
    if reject_category:
        destination.reload()
        metadata = dict(destination.metadata or {})
        metadata.update(
            {
                "dagster_reject_category": reject_category[:80],
                "dagster_rejected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        destination.metadata = metadata
        destination.patch(if_metageneration_match=destination.metageneration)
    source.delete(if_generation_match=generation)
    return destination


def classify_exception(exc: BaseException) -> str:
    """Return permanent, transient, or unknown for retry decisions."""
    if isinstance(exc, InputValidationError):
        return "permanent"
    if isinstance(exc, (google_exceptions.BadRequest, google_exceptions.Forbidden, google_exceptions.Unauthorized)):
        return "permanent"
    if isinstance(exc, google_exceptions.NotFound):
        return "permanent"
    if isinstance(
        exc,
        (
            google_exceptions.TooManyRequests,
            google_exceptions.InternalServerError,
            google_exceptions.BadGateway,
            google_exceptions.ServiceUnavailable,
            google_exceptions.GatewayTimeout,
            google_exceptions.DeadlineExceeded,
        ),
    ):
        return "transient"
    return "unknown"
