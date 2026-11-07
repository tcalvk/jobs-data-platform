"""Storage-only ADC resource; client creation is execution-time only."""

from dagster import ConfigurableResource


class GdeltStorageResource(ConfigurableResource):
    project_id: str | None = None

    @property
    def storage_client(self):
        from google.cloud import storage
        return storage.Client(project=self.project_id)
