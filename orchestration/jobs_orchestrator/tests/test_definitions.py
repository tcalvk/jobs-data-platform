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


if __name__ == "__main__":
    unittest.main()
