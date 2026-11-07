"""Manual production ingestion, separate from the resource-free M1 inspector."""

from dagster import Config, MaterializeResult, asset, define_asset_job

from jobs_orchestrator.resources.gdelt_storage import GdeltStorageResource
from .pipeline import ingest_latest


class GkgIngestConfig(Config):
    bucket: str = "jobs_data_platform_prod"
    temp_dir: str | None = None


@asset(group_name="gdelt_gkg")
def gdelt_gkg_ingest(config: GkgIngestConfig, gdelt_storage: GdeltStorageResource) -> MaterializeResult:
    return MaterializeResult(metadata=ingest_latest(gdelt_storage, config.bucket, config.temp_dir))


gdelt_gkg_ingest_job = define_asset_job("gdelt_gkg_ingest_job", selection=[gdelt_gkg_ingest])
