"""Explicit Dagster definitions for this code location."""

import os
from pathlib import Path

from dagster import Definitions, EnvVar

if os.getenv("DAGSTER_ENVIRONMENT") == "dev":
    # The externally supplied bootstrap value is intentionally checked before dotenv.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env.dev", override=False)

from jobs_orchestrator.assets.serpapi_load_jobs.asset import (
    serpapi_load_jobs,
    serpapi_load_jobs_job,
)
from jobs_orchestrator.assets.serpapi_load_jobs.sensor import serpapi_load_jobs_sensor
from jobs_orchestrator.resources.duckdb_check import DuckDBCheckResource
from jobs_orchestrator.resources.gcp import GcpResource
from jobs_orchestrator.resources.slack_notifications import SlackNotificationsResource


def _optional_slack_enabled() -> bool:
    return os.getenv("SLACK_NOTIFICATIONS_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _optional_slack_timeout() -> float:
    try:
        return float(os.getenv("SLACK_NOTIFICATION_TIMEOUT_SECONDS", "3"))
    except ValueError:
        # Invalid optional notification config must not prevent core definitions
        # from loading; delivery will use the short default timeout.
        return 3.0


gcp_resource = GcpResource(
    environment=EnvVar("DAGSTER_ENVIRONMENT"),
    project_id=EnvVar("GCP_PROJECT_ID"),
    bucket_name=EnvVar("GCS_BUCKET"),
    incoming_prefix=EnvVar("GCS_INCOMING_PREFIX"),
    archive_prefix=EnvVar("GCS_ARCHIVE_PREFIX"),
    reject_prefix=EnvVar("GCS_REJECT_PREFIX"),
    raw_table_id=EnvVar("BQ_RAW_TABLE_ID"),
    production_project_id=EnvVar("PRODUCTION_GCP_PROJECT_ID"),
    production_bucket=EnvVar("PRODUCTION_GCS_BUCKET"),
)
duckdb_check_resource = DuckDBCheckResource()
slack_notifications_resource = SlackNotificationsResource(
    enabled=_optional_slack_enabled(),
    timeout_seconds=_optional_slack_timeout(),
)

defs = Definitions(
    assets=[serpapi_load_jobs],
    jobs=[serpapi_load_jobs_job],
    sensors=[serpapi_load_jobs_sensor],
    resources={
        "gcp": gcp_resource,
        "duckdb_check": duckdb_check_resource,
        "slack_notifications": slack_notifications_resource,
    },
)
