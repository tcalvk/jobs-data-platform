"""Manual sample job; deliberately has no GCP resources or persisted output."""

from dagster import AssetSelection, Config, MaterializeResult, MetadataValue, asset, define_asset_job

from .sample import DEFAULT_OUTPUT_DIR, obtain_latest_sample


class GdeltSampleConfig(Config):
    output_dir: str = DEFAULT_OUTPUT_DIR


@asset(group_name="gdelt_gkg")
def gdelt_gkg_sample(config: GdeltSampleConfig) -> MaterializeResult:
    summary = obtain_latest_sample(config.output_dir)
    return MaterializeResult(metadata={
        key: MetadataValue.json(value) if isinstance(value, (dict, list)) else value
        for key, value in summary.items()
    })


gdelt_gkg_sample_job = define_asset_job(
    "gdelt_gkg_sample_job", selection=AssetSelection.assets(gdelt_gkg_sample)
)
