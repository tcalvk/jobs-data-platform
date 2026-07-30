"""Generation-aware GCS discovery sensor for the SerpApi loader."""

from __future__ import annotations

import json

from dagster import RunRequest, SensorEvaluationContext, SensorResult, sensor

from jobs_orchestrator.assets.serpapi_load_jobs.asset import serpapi_load_jobs_job
from jobs_orchestrator.assets.serpapi_load_jobs.file_processing import is_directory_placeholder
from jobs_orchestrator.resources.gcp import GcpResource


MAX_RUNS_PER_TICK = 100
WORKLOAD_TAG = "serpapi_load_jobs"


def _identity(bucket: str, name: str, generation: int | str) -> str:
    return f"{bucket}\u001f{name}\u001f{generation}"


def _cursor_identities(cursor: str | None) -> set[str]:
    if not cursor:
        return set()
    try:
        parsed = json.loads(cursor)
        values = parsed.get("emitted", [])
        return {value for value in values if isinstance(value, str)}
    except (TypeError, ValueError):
        return set()


@sensor(
    name="serpapi_load_jobs_sensor",
    job=serpapi_load_jobs_job,
    minimum_interval_seconds=1800,
)
def serpapi_load_jobs_sensor(
    context: SensorEvaluationContext, gcp: GcpResource
) -> SensorResult:
    prefix = gcp.normalized_incoming_prefix + "/"
    candidates = [
        blob
        for blob in gcp.storage_client.list_blobs(gcp.bucket_name, prefix=prefix)
        if not is_directory_placeholder(blob) and blob.generation is not None
    ]
    candidates.sort(key=lambda blob: (blob.time_created, blob.name))
    current = {
        _identity(gcp.bucket_name, blob.name, blob.generation): blob for blob in candidates
    }
    emitted = _cursor_identities(context.cursor).intersection(current)
    unseen = [blob for identity, blob in current.items() if identity not in emitted]
    unseen.sort(key=lambda blob: (blob.time_created, blob.name))

    requests = []
    for blob in unseen[:MAX_RUNS_PER_TICK]:
        identity = _identity(gcp.bucket_name, blob.name, blob.generation)
        emitted.add(identity)
        requests.append(
            RunRequest(
                run_key=identity,
                run_config={
                    "ops": {
                        "serpapi_load_jobs": {
                            "config": {"object_name": blob.name, "generation": int(blob.generation)}
                        }
                    }
                },
                tags={"environment": gcp.environment, "workload": WORKLOAD_TAG},
            )
        )
    return SensorResult(run_requests=requests, cursor=json.dumps({"emitted": sorted(emitted)}))
