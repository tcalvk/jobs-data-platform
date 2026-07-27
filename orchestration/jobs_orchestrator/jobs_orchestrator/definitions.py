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
from jobs_orchestrator.resources.gcp import GcpResource

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

defs = Definitions(
    assets=[serpapi_load_jobs],
    jobs=[serpapi_load_jobs_job],
    sensors=[serpapi_load_jobs_sensor],
    resources={"gcp": gcp_resource},
)
