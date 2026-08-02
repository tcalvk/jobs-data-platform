"""The one-object-at-a-time SerpApi GCS to BigQuery Dagster asset."""

import os
import random
from html import escape
from ipaddress import IPv4Address, IPv6Address
from pathlib import PurePosixPath
from string import hexdigits
from typing import BinaryIO
from urllib.parse import quote, urlsplit

from dagster import AssetExecutionContext, Config, Failure, MaterializeResult, RetryRequested, asset, define_asset_job
from dagster import AssetSelection
from google.api_core import exceptions as google_exceptions
from google.cloud import bigquery

from jobs_orchestrator.assets.serpapi_load_jobs.file_processing import (
    InputValidationError,
    classify_exception,
    close_and_remove_tempfile,
    copy_then_delete_generation,
    ensure_prefix_markers,
    is_supported_jsonl,
    lifecycle_object_name,
    transform_jsonl_to_tempfile,
)
from jobs_orchestrator.assets.serpapi_load_jobs.serpapi_checks import SERPAPI_CHECKS
from jobs_orchestrator.resources.duckdb_check import (
    DuckDBCheckExecutionError,
    DuckDBCheckResource,
)
from jobs_orchestrator.resources.gcp import GcpResource
from jobs_orchestrator.resources.slack_notifications import SlackNotificationsResource


class SerpapiLoadJobsConfig(Config):
    object_name: str
    generation: int


def _uri(bucket: str, object_name: str) -> str:
    return f"gs://{bucket}/{object_name}"


def _retry_delay(retry_number: int) -> float:
    return (60 if retry_number == 0 else 120) + random.uniform(0, 10)


# Bounds a stuck upload/completion within one Dagster attempt. Dagster-level retries
# remain responsible for the three total attempts.
BIGQUERY_REQUEST_TIMEOUT_SECONDS = 60
BIGQUERY_JOB_TIMEOUT_SECONDS = 600
ASSET_NAME = "serpapi_load_jobs"


def _notification_value(value: object, maximum_length: int = 700) -> str:
    """Make bounded object metadata safe for Slack mrkdwn without exposing content."""
    normalized = " ".join(str(value).split())
    if len(normalized) > maximum_length:
        normalized = normalized[: maximum_length - 3] + "..."
    return escape(normalized, quote=False)


def _configured_run_url(run_id: str) -> str | None:
    """Build a run link only from an explicitly configured, safe Dagster web URL."""
    base_url = os.getenv("DAGSTER_WEB_URL", "").strip()
    if (
        not base_url
        or "\\" in base_url
        or "?" in base_url
        or "#" in base_url
        or any(
            ord(character) <= 32 or ord(character) == 127
            for character in base_url
        )
        or any(
            character == "%"
            and (
                index + 2 >= len(base_url)
                or base_url[index + 1] not in hexdigits
                or base_url[index + 2] not in hexdigits
            )
            for index, character in enumerate(base_url)
        )
    ):
        return None
    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        port = parsed.port  # Access validates malformed and out-of-range ports.
        username = parsed.username
        password = parsed.password
    except (UnicodeError, ValueError):
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.netloc.endswith(":")
    ):
        return None
    if username is not None or password is not None or parsed.query or parsed.fragment:
        return None
    if port is not None and not 0 <= port <= 65535:
        return None

    is_local_host = False
    try:
        if ":" in hostname:
            is_local_host = IPv6Address(hostname).is_loopback
        else:
            ascii_hostname = hostname.rstrip(".").encode("idna").decode("ascii")
            labels = ascii_hostname.split(".")
            if len(labels) == 4 and all(label.isdigit() for label in labels):
                is_local_host = IPv4Address(ascii_hostname).is_loopback
            elif ascii_hostname.lower() == "localhost":
                is_local_host = True
            if (
                not ascii_hostname
                or len(ascii_hostname) > 253
                or any(
                    not label
                    or len(label) > 63
                    or label.startswith("-")
                    or label.endswith("-")
                    or not all(character.isalnum() or character == "-" for character in label)
                    for label in labels
                )
            ):
                return None
    except (UnicodeError, ValueError):
        return None
    if parsed.scheme == "http" and not is_local_host:
        return None
    return f"{base_url.rstrip('/')}/runs/{quote(run_id, safe='')}"


def _rejection_notification(
    *,
    environment: str,
    rejected_object_name: str,
    rejected_uri: str,
    source_generation: int,
    category: str,
    run_id: str,
) -> str:
    """Compose the SerpApi file-rejection policy message."""
    lines = [
        ":warning: Dagster rejected a SerpApi input file",
        f"*Environment:* {_notification_value(environment)}",
        f"*Asset:* {ASSET_NAME}",
        f"*Rejected filename:* {_notification_value(PurePosixPath(rejected_object_name).name)}",
        f"*Rejected object path:* {_notification_value(rejected_object_name)}",
        f"*Rejected GCS URI:* {_notification_value(rejected_uri)}",
        f"*Source generation:* {_notification_value(source_generation)}",
        f"*Rejection category:* {_notification_value(category)}",
        f"*Dagster run ID:* {_notification_value(run_id)}",
    ]
    run_url = _configured_run_url(run_id)
    if run_url is not None:
        lines.append(f"*Dagster run:* {_notification_value(run_url)}")
    return "\n".join(lines)


@asset(name="serpapi_load_jobs", group_name="serpapi")
def serpapi_load_jobs(
    context: AssetExecutionContext,
    config: SerpapiLoadJobsConfig,
    gcp: GcpResource,
    duckdb_check: DuckDBCheckResource,
    slack_notifications: SlackNotificationsResource,
) -> MaterializeResult:
    """Fully validate, append, then archive one exact GCS object generation."""
    bucket = gcp.bucket()
    source_uri = _uri(gcp.bucket_name, config.object_name)
    archive_name = lifecycle_object_name(
        config.object_name, gcp.normalized_incoming_prefix, gcp.normalized_archive_prefix
    )
    reject_name = lifecycle_object_name(
        config.object_name, gcp.normalized_incoming_prefix, gcp.normalized_reject_prefix
    )
    attempt = context.retry_number + 1
    transformed: BinaryIO | None = None
    loaded = False

    def reject(category: str) -> None:
        destination = copy_then_delete_generation(
            bucket,
            config.object_name,
            config.generation,
            reject_name,
            reject_category=category,
        )
        rejected_uri = _uri(gcp.bucket_name, reject_name)
        context.log.error(
            "Rejected %s generation %s to gs://%s/%s (destination generation %s; category=%s)",
            source_uri,
            config.generation,
            gcp.bucket_name,
            reject_name,
            destination.generation,
            category,
        )
        # The move helper returns only after the generation-safe copy, reject
        # metadata patch, and exact-generation source delete have all succeeded.
        # Slack is deliberately outside rejection semantics and never retried here.
        try:
            slack_notifications.send_message(
                _rejection_notification(
                    environment=gcp.environment,
                    rejected_object_name=reject_name,
                    rejected_uri=rejected_uri,
                    source_generation=config.generation,
                    category=category,
                    run_id=context.run_id,
                )
            )
        except Exception as notification_error:
            context.log.error(
                "Slack rejection notification failed for %s generation %s; "
                "the completed file rejection is unchanged (error_type=%s).",
                source_uri,
                config.generation,
                type(notification_error).__name__,
            )

    try:
        context.log.info(
            "Processing %s generation %s in %s (attempt %s/3).",
            source_uri,
            config.generation,
            gcp.environment,
            attempt,
        )
        ensure_prefix_markers(
            bucket, gcp.normalized_archive_prefix, gcp.normalized_reject_prefix
        )
        if not is_supported_jsonl(config.object_name):
            raise InputValidationError("unsupported_extension", "Only lowercase .jsonl files are supported.")

        source = bucket.blob(config.object_name, generation=config.generation)
        try:
            source.reload()  # An absent generation is a stale run and must not touch a newer upload.
        except google_exceptions.NotFound as exc:
            raise Failure(
                description=(
                    f"Observed generation {config.generation} for {source_uri} no longer exists; "
                    "the run did not move a newer upload."
                )
            ) from exc
        transformed, row_count = transform_jsonl_to_tempfile(source, source_uri)
        check_result = duckdb_check.run_checks(transformed, SERPAPI_CHECKS)
        if not check_result.passed:
            failed_checks = ", ".join(
                f"{check.name}={check.failed_row_count}"
                for check in check_result.checks
                if check.failed_row_count
            )
            raise InputValidationError(
                "duckdb_check_failed",
                f"DuckDB validation failed for {check_result.row_count} rows: {failed_checks}.",
            )
        load_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
        )
        transformed.seek(0)
        load_job = gcp.bigquery_client.load_table_from_file(
            transformed,
            gcp.raw_table_id,
            job_config=load_config,
            timeout=BIGQUERY_REQUEST_TIMEOUT_SECONDS,
        )
        load_job.result(timeout=BIGQUERY_JOB_TIMEOUT_SECONDS)
        loaded = True

        copy_then_delete_generation(
            bucket, config.object_name, config.generation, archive_name
        )
        archive_uri = _uri(gcp.bucket_name, archive_name)
        context.log.info(
            "Loaded %s rows from %s to %s and archived it at %s.",
            row_count,
            source_uri,
            load_job.job_id,
            archive_uri,
        )
        return MaterializeResult(
            metadata={
                "source_uri": source_uri,
                "archive_uri": archive_uri,
                "row_count": row_count,
                "bigquery_job_id": load_job.job_id,
                "attempt": attempt,
            }
        )
    except DuckDBCheckExecutionError as exc:
        if context.retry_number < 2:
            delay = _retry_delay(context.retry_number)
            context.log.warning(
                "DuckDB validation was inconclusive for %s on attempt %s/3: %s. "
                "Retrying in %.1fs.",
                source_uri,
                attempt,
                exc,
                delay,
            )
            raise RetryRequested(max_retries=2, seconds_to_wait=delay) from exc
        raise Failure(
            description=(
                f"DuckDB validation remained inconclusive after three attempts for {source_uri}; "
                "the source remains incoming and was not submitted to BigQuery."
            )
        ) from exc
    except InputValidationError as exc:
        # Input is never retried. A failed reject move deliberately leaves the source incoming.
        reject(exc.category)
        raise Failure(description=f"Rejected {source_uri}: {exc}") from exc
    except Exception as exc:
        classification = classify_exception(exc)
        if classification == "permanent":
            # Invalid BQ requests and authorization/configuration failures are not retryable.
            reject("permanent_request_failure")
            raise Failure(description=f"Permanent failure for {source_uri}: {exc}") from exc

        if context.retry_number < 2:
            delay = _retry_delay(context.retry_number)
            context.log.warning(
                "Transient/unknown failure for %s on attempt %s/3: %s. Retrying in %.1fs.",
                source_uri,
                attempt,
                exc,
                delay,
            )
            raise RetryRequested(max_retries=2, seconds_to_wait=delay) from exc

        category = "post_load_archive_failure" if loaded else "transient_failure_exhausted"
        # If this fails, propagate it: the source remains incoming for a manual re-execution.
        reject(category)
        raise Failure(
            description=f"Failed after three attempts and rejected {source_uri}: {exc}"
        ) from exc
    finally:
        close_and_remove_tempfile(transformed)


serpapi_load_jobs_job = define_asset_job(
    "serpapi_load_jobs_job",
    selection=AssetSelection.assets(serpapi_load_jobs),
    tags={"workload": "serpapi_load_jobs"},
)
