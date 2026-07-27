# Jobs Orchestrator

`serpapi_load_jobs` validates one incoming SerpApi JSONL object, appends it to
the raw BigQuery table in one load job, then moves that exact GCS generation to
archive or reject. Delivery is at-least-once: retries after a successful load
can append duplicates, which downstream dbt must deduplicate.

## Local demo development

Use Python 3.11 (or compatible Python 3.12) and install this project separately:

```bash
cd orchestration/jobs_orchestrator
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
gcloud auth application-default login
cp .env.dev.example .env.dev
```

Fill `.env.dev` with demo-only values; it is gitignored. Export the bootstrap
environment value so definitions can load that file:

```bash
DAGSTER_ENVIRONMENT=dev .venv/bin/dagster dev
```

Open <http://localhost:3000>, enable `serpapi_load_jobs_sensor`, and use
**Evaluate now** for a smoke check. Its normal minimum polling interval is four
hours. The configured bucket must already exist. The producer owns
`serpapi/incoming/`; this asset creates archive/reject marker objects only.
It never creates buckets, datasets, tables, or the incoming marker.

`BQ_RAW_TABLE_ID` must be fully qualified and match `GCP_PROJECT_ID`. The raw
table must already have this practical schema:

```sql
created_at TIMESTAMP,
job_data JSON,
query_version_id INT64,
gcs_uri STRING
```

Transformed JSONL uses `/var/tmp/jobs-orchestrator`, with disk use proportional
to the largest source object plus transformation overhead. Provision it
accordingly. BigQuery upload requests time out after 60 seconds and job
completion waits time out after 10 minutes; those failures use the normal
three-attempt retry policy. Invalid UTF-8, malformed/non-object JSON, blank-only files, and
non-`.jsonl` files move to reject. If a reject move fails, the source remains
incoming: fix the storage failure and manually re-execute that generation.

## Ubuntu standalone deployment

`deploy/` provides templates for one localhost-bound gRPC code server, daemon,
and webserver. This is neither a container nor a production cutover.

1. Verify Python 3.11 and the pinned Dagster compatibility; create a `dagster`
   user and check out the repository at `/opt/jobs-data-platform`.
2. Use a compatible `/opt/jobs-data-platform/.venv`, create
   `/var/lib/dagster/storage`, `/var/lib/dagster/compute_logs`, and
   `/etc/jobs-orchestrator`, all with restrictive `dagster` ownership.
3. Install `deploy/dagster.yaml.example` as `$DAGSTER_HOME/dagster.yaml` and
   `deploy/workspace.yaml.example` as `/var/lib/dagster/workspace.yaml`.
4. Create `/etc/jobs-orchestrator/environment` outside Git with the complete
   environment contract and `GOOGLE_APPLICATION_CREDENTIALS` pointing to a
   `dagster`-owned service-account file with mode `0600` or stricter.
5. Install the three systemd templates, run `systemctl daemon-reload`, enable,
   and start them. Use an SSH tunnel to access the localhost-only UI unless a
   separately secured reverse proxy is introduced.

SQLite storage must be local persistent disk, never a network filesystem. Back
up `/var/lib/dagster/storage` only while services are stopped or with a
SQLite-safe method. The service account needs bucket-scoped
`storage.objects.list/get/create/delete/update`, project-level
`bigquery.jobs.create`, and destination permissions `bigquery.tables.get` and
`bigquery.tables.updateData`. Provision resources and permissions manually.
