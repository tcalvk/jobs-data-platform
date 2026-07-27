"""Shared, environment-aware GCP configuration for Dagster assets and sensors."""

from __future__ import annotations

from functools import cached_property

from dagster import ConfigurableResource
from google.cloud import bigquery, storage


def _normalized_prefix(value: str, label: str) -> str:
    prefix = value.strip().strip("/")
    if not prefix:
        raise ValueError(f"{label} must be a non-empty GCS prefix.")
    return prefix


class GcpResource(ConfigurableResource):
    """Validated configuration and lazily-created clients using ADC credentials."""

    environment: str
    project_id: str
    bucket_name: str
    incoming_prefix: str = "serpapi/incoming"
    archive_prefix: str = "serpapi/archive"
    reject_prefix: str = "serpapi/reject"
    raw_table_id: str
    production_project_id: str = ""
    production_bucket: str = ""

    def setup_for_execution(self, _context) -> None:
        environment = self.environment.strip().lower()
        if environment not in {"dev", "prod"}:
            raise ValueError("DAGSTER_ENVIRONMENT must be either 'dev' or 'prod'.")
        if not self.project_id.strip() or not self.bucket_name.strip():
            raise ValueError("GCP_PROJECT_ID and GCS_BUCKET are required.")

        table_parts = self.raw_table_id.strip().split(".")
        if len(table_parts) != 3 or not all(table_parts):
            raise ValueError(
                "BQ_RAW_TABLE_ID must be fully qualified as project.dataset.table."
            )
        if table_parts[0] != self.project_id.strip():
            raise ValueError("BQ_RAW_TABLE_ID project must match GCP_PROJECT_ID.")

        prefixes = [
            _normalized_prefix(self.incoming_prefix, "GCS_INCOMING_PREFIX"),
            _normalized_prefix(self.archive_prefix, "GCS_ARCHIVE_PREFIX"),
            _normalized_prefix(self.reject_prefix, "GCS_REJECT_PREFIX"),
        ]
        if len(set(prefixes)) != len(prefixes):
            raise ValueError("Incoming, archive, and reject prefixes must be distinct.")
        if environment == "dev":
            production_project = self.production_project_id.strip()
            production_bucket = self.production_bucket.strip()
            if not production_project or not production_bucket:
                raise ValueError(
                    "PRODUCTION_GCP_PROJECT_ID and PRODUCTION_GCS_BUCKET are required in dev "
                    "to prevent accidental production targeting."
                )
            if (
                self.project_id.strip() == production_project
                or self.bucket_name.strip() == production_bucket
            ):
                raise ValueError("Dev configuration must not target a production project or bucket.")

    @property
    def normalized_incoming_prefix(self) -> str:
        return _normalized_prefix(self.incoming_prefix, "GCS_INCOMING_PREFIX")

    @property
    def normalized_archive_prefix(self) -> str:
        return _normalized_prefix(self.archive_prefix, "GCS_ARCHIVE_PREFIX")

    @property
    def normalized_reject_prefix(self) -> str:
        return _normalized_prefix(self.reject_prefix, "GCS_REJECT_PREFIX")

    @cached_property
    def storage_client(self) -> storage.Client:
        return storage.Client(project=self.project_id)

    @cached_property
    def bigquery_client(self) -> bigquery.Client:
        return bigquery.Client(project=self.project_id)

    def bucket(self) -> storage.Bucket:
        return self.storage_client.bucket(self.bucket_name)
