import unittest

from dagster import Definitions

from jobs_orchestrator.definitions import defs
from jobs_orchestrator.resources.duckdb_check import DuckDBCheckResource
from jobs_orchestrator.resources.slack_notifications import SlackNotificationsResource


class DefinitionsTests(unittest.TestCase):
    def test_duckdb_check_resource_is_registered_and_definitions_are_loadable(self):
        self.assertIsInstance(defs.resources["duckdb_check"], DuckDBCheckResource)
        self.assertIsInstance(
            defs.resources["slack_notifications"], SlackNotificationsResource
        )
        Definitions.validate_loadable(defs)

    def test_sample_job_selects_only_manual_gdelt_asset(self):
        from dagster import AssetKey

        job = defs.resolve_job_def("gdelt_gkg_sample_job")
        self.assertEqual(job.asset_layer.executable_asset_keys, {AssetKey("gdelt_gkg_sample")})
        self.assertEqual(len(defs.sensors), 1)  # Existing SerpAPI sensor only.
        self.assertFalse(defs.schedules)


if __name__ == "__main__":
    unittest.main()
