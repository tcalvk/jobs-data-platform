# Dagster `serpapi_load_jobs` Implementation Plan

## Goal

Implement the existing GCS-to-BigQuery load behavior as a reliable, self-hosted Dagster asset named `serpapi_load_jobs`.

The asset will process one object per run, append the transformed records to the existing raw BigQuery table, and move the source object from an incoming prefix to either an archive or reject prefix. A polling sensor will discover incoming objects every four hours.

This plan delivers a working Dagster implementation in a demo GCP environment and a standalone Ubuntu deployment managed by `systemd`. Production cutover is intentionally separate.

## Confirmed Decisions

- Run Dagster standalone on an Ubuntu home server.
- Use separate `systemd` services for the Dagster webserver, daemon, and code server.
- Use persistent SQLite files beneath `DAGSTER_HOME` for Dagster run, event, schedule, and sensor state.
- Do not containerize this deployment.
- Use environment-specific configuration; local development targets a demo GCP project.
- Use ADC locally and a dedicated least-privilege service account on the server.
- Process one GCS object per Dagster run, sequentially.
- Poll GCS every four hours and enqueue at most ten newly observed objects per sensor tick.
- Prevent duplicate launches for the same observed upload, but process a later re-upload of the same object name.
- Use one bucket with `serpapi/incoming/`, `serpapi/archive/`, and `serpapi/reject/` prefixes.
- Have the Dagster asset idempotently create zero-byte `serpapi/archive/` and `serpapi/reject/` marker objects when absent; the producer owns `serpapi/incoming/`.
- Allow archive and reject objects to overwrite an existing destination with the same relative name.
- Validate the complete file before loading and submit one BigQuery append load job per file.
- Reject malformed, empty, blank-only, and unsupported files.
- Perform no additional business-field validation in this scope.
- Preserve the existing raw-table output contract.
- Remove the BigQuery load ledger from the Dagster implementation.
- Accept at-least-once delivery; downstream dbt models own deduplication.
- Use three total attempts for transient failures, with approximately one- and two-minute retry delays plus jitter.
- Keep observability basic: filename, source/destination, row count, attempts, and outcome in Dagster logs/materialization metadata.
- Do not add automated tests in this project; verify manually against the demo environment.
- Do not create GCS buckets or BigQuery tables automatically.
- Do not cut over production or remove/modify the legacy Cloud Run loader in this project.

## Current State

### Legacy loader

The parallel replacement candidate is `dags/ao/gcs_to_bq_load.py`.

It currently:

1. lists every lowercase `.jsonl` object under `GCS_PREFIX`;
2. fetches object names from a BigQuery ledger;
3. skips ledgered names;
4. parses objects line by line, silently skipping malformed JSON;
5. maps each source record to four raw-table columns;
6. appends records in 500-row BigQuery load jobs;
7. inserts a ledger row after all batches succeed;
8. leaves source objects in place;
9. catches per-object errors and still allows the overall task to exit successfully.

The dispatcher maps `gcs_to_bq_load` to that module in `controller.py`. Leave both files unchanged in this project because production cutover and retirement are out of scope.

### Dagster scaffold

The Dagster project is under `orchestration/jobs_orchestrator/` and currently contains:

- an empty `jobs_orchestrator/assets.py`;
- a minimal `jobs_orchestrator/definitions.py`;
- unpinned `dagster` and `dagster-cloud` dependencies;
- no assets, sensors, jobs, resources, instance configuration, or deployment units.

### Existing BigQuery contract

Continue writing these columns:

| Column | Value |
|---|---|
| `created_at` | `record.get("fetched_at")` |
| `job_data` | The complete source JSON object |
| `query_version_id` | `record.get("query_id")` |
| `gcs_uri` | The original incoming `gs://` URI |

The expected practical schema is:

```sql
created_at TIMESTAMP,
job_data JSON,
query_version_id INT64,
gcs_uri STRING
```

The implementation must not create or alter this table. The manual setup documentation should state the required schema.

## Scope

### In scope

- New `serpapi_load_jobs` Dagster asset and asset job.
- GCS polling sensor.
- Custom GCP resource/configuration layer.
- Full-file JSONL validation with bounded memory and temporary disk proportional to the transformed file size.
- One BigQuery load job per source file.
- GCS archive/reject movement and rejection metadata.
- Retry classification and three-total-attempt behavior.
- Asset-focused package reorganization.
- Demo environment configuration and manual smoke verification.
- Standalone SQLite-backed Dagster deployment on Ubuntu with `systemd`.
- Updated orchestrator dependencies and operating documentation.

### Out of scope

- Production cutover, producer changes, dual-running coordination, or rollback.
- Removal or modification of `controller.py` or `dags/ao/gcs_to_bq_load.py`.
- Docker, Docker Compose, or multiple Dagster instances.
- Automated bucket, dataset, or table provisioning, or creation of the producer-owned incoming prefix marker.
- BigQuery-ledger writes or migration of old ledger data.
- Exactly-once loading or loader-side deduplication.
- Strict validation of `fetched_at`, `query_id`, `job`, or other business fields.
- dbt model changes.
- Unit, integration, or CI test suites.
- External alerts, paging, dashboards, or advanced retention management.

## Target Architecture

### File layout

Replace the single empty `assets.py` module with an assets package organized by asset domain:

```text
orchestration/jobs_orchestrator/
├── .env.dev.example
├── pyproject.toml
├── README.md
├── deploy/
│   ├── dagster.yaml.example
│   ├── workspace.yaml.example
│   ├── jobs-orchestrator-code.service
│   ├── jobs-orchestrator-daemon.service
│   └── jobs-orchestrator-webserver.service
└── jobs_orchestrator/
    ├── __init__.py
    ├── definitions.py
    ├── assets/
    │   ├── __init__.py
    │   └── serpapi_load_jobs/
    │       ├── __init__.py
    │       ├── asset.py
    │       ├── sensor.py
    │       └── file_processing.py
    └── resources/
        ├── __init__.py
        └── gcp.py
```

Delete `jobs_orchestrator/assets.py` when adding `jobs_orchestrator/assets/`; Python cannot safely use both forms for the same module name.

### Runtime flow

1. The sensor lists objects recursively beneath the configured incoming prefix.
2. It ignores directory placeholder objects and sorts real objects by creation time, oldest first.
3. It compares current `(bucket, object name, generation)` identities with the bounded set of still-incoming identities recorded in its cursor and emits at most ten unseen identities per tick.
4. Each run request includes object name and generation in run config and carries a deterministic run key based on bucket, object name, and generation.
5. Run tags identify the workload and configured environment.
6. A queued-run tag concurrency limit permits only one `serpapi_load_jobs` run at a time.
7. The asset ensures zero-byte marker objects exist for the normalized archive and reject prefixes, without creating an incoming marker.
8. The asset reads the exact observed generation and validates all nonblank lines.
9. It writes transformed target rows to a temporary newline-delimited JSON file without accumulating the whole object in memory.
10. It submits that temporary file as one append load job to BigQuery and waits for completion.
11. It copies the source to the corresponding archive path, allowing destination overwrite, then deletes only the source generation that was processed.
12. It logs/materializes basic metadata and removes temporary files in a `finally` block.

If validation fails, the asset moves the source to the equivalent reject path, adds rejection metadata, and reports the Dagster run as failed without retrying. If a transient operation fails, it retries up to the three-total-attempt limit. On the third failed attempt it moves the source to reject instead of requesting another retry, then reports failure. Only successful loads followed by successful archive movement materialize the asset; rejected runs only log failure details.

## Environment Contract

Use these environment variables in both development and server deployments:

| Variable | Purpose |
|---|---|
| `DAGSTER_ENVIRONMENT` | Required `dev` or `prod` label and safety context |
| `GCP_PROJECT_ID` | GCP project used by GCS and BigQuery clients |
| `GCS_BUCKET` | Bucket containing all three lifecycle prefixes |
| `GCS_INCOMING_PREFIX` | Default `serpapi/incoming` |
| `GCS_ARCHIVE_PREFIX` | Default `serpapi/archive` |
| `GCS_REJECT_PREFIX` | Default `serpapi/reject` |
| `BQ_RAW_TABLE_ID` | Fully qualified `project.dataset.table` destination |
| `GOOGLE_APPLICATION_CREDENTIALS` | Server-only path to the service-account JSON file |
| `PRODUCTION_GCP_PROJECT_ID` | Production project used by the local-dev safety check |
| `PRODUCTION_GCS_BUCKET` | Production bucket used by the local-dev safety check |

Implementation requirements:

- Add `.env.dev` to the root `.gitignore` pattern set; commit only `.env.dev.example` with placeholders.
- Start local development with `DAGSTER_ENVIRONMENT=dev dagster dev`; that externally supplied bootstrap value permits loading `.env.dev` before resource values are resolved.
- Load `.env.dev` only when the externally supplied `DAGSTER_ENVIRONMENT` equals `dev` and only for local development.
- Do not load dotenv automatically in production.
- Require fully qualified `BQ_RAW_TABLE_ID` and verify that its project component matches `GCP_PROJECT_ID`.
- When `DAGSTER_ENVIRONMENT=dev`, reject configured project/bucket values equal to the explicit production guard values.
- Normalize prefixes by stripping leading/trailing `/`, then verify that incoming, archive, and reject prefixes are nonempty and distinct.
- Do not place credentials or real environment files in Git.
- Keep SQLite instance files outside the repository under `/var/lib/dagster/storage`, owned by the dedicated `dagster` user.
- Ensure only this Dagster instance uses that SQLite storage directory.

Future production topology, documented for configuration compatibility but not activated in this project:

```text
gs://jobs_data_platform_prod/serpapi/incoming/<relative-path>
gs://jobs_data_platform_prod/serpapi/archive/<relative-path>
gs://jobs_data_platform_prod/serpapi/reject/<relative-path>
```

Demo bucket and table identifiers remain deployment inputs; do not invent or hard-code them. Install and verify the standalone server with `DAGSTER_ENVIRONMENT=dev` and demo GCP resources in this project. Creating or starting a server environment that targets production is part of the separate cutover effort.

## Detailed Implementation Steps

### 1. Align and pin orchestrator dependencies

Update `orchestration/jobs_orchestrator/pyproject.toml`:

- pin `dagster==1.13.15` and make `dagster-webserver==1.13.15` a server runtime dependency rather than a dev-only dependency;
- add compatible, reproducibly pinned `google-cloud-storage`, `google-cloud-bigquery`, and `python-dotenv` versions;
- remove the unused `dagster-cloud` dependency;
- keep server runtime dependencies installable from this project without relying on root `requirements.txt`;
- target the server's selected Python version, preferably Python 3.11 to match `Dockerfile.prod`.

Do not add testing dependencies or test work solely for this change.

### 2. Add environment-aware GCP resource configuration

Create `jobs_orchestrator/resources/gcp.py` with a typed Dagster configurable resource or equivalent small configuration object that:

- receives all environment values through Dagster `EnvVar` bindings;
- validates the environment, fully qualified table ID, and lifecycle prefixes when the resource is initialized; do not incorrectly depend on deferred Dagster `EnvVar` values being available during module import;
- enforces the local-dev production-target guard;
- creates BigQuery and Storage clients using ADC/default credential discovery and explicit `project=GCP_PROJECT_ID`;
- exposes normalized bucket/prefix/table values to the asset and sensor;
- does not create buckets, datasets, or tables; archive/reject marker creation is the only allowed cloud-structure initialization.

Keep client construction centralized so the sensor and asset use identical configuration and authentication behavior.

### 3. Implement file-processing helpers

Create `jobs_orchestrator/assets/serpapi_load_jobs/file_processing.py` for behavior that does not need Dagster decorators.

Implement focused helpers for:

- confirming that an object is beneath the incoming prefix;
- deriving its relative path;
- mapping the relative path to archive/reject object names;
- detecting directory placeholders;
- classifying supported `.jsonl` names;
- ensuring archive/reject zero-byte prefix marker objects exist idempotently;
- streaming and validating UTF-8 JSONL;
- constructing the four-column BigQuery row;
- writing transformed JSONL to a named temporary file;
- copying an object within the bucket and deleting the exact source generation;
- attaching concise reject metadata;
- classifying known permanent versus transient GCP/API failures.

Validation rules:

- ignore blank lines;
- reject invalid UTF-8;
- reject any nonblank line that is invalid JSON;
- reject nonstandard JSON constants such as `NaN`, `Infinity`, and `-Infinity` during parsing, and serialize with `allow_nan=False`;
- reject any decoded value that is not a JSON object;
- reject the complete file if no records remain;
- do not validate required business keys or nested SerpApi structure;
- do not load any rows until the entire object has passed validation.

The transformed temporary file must contain one JSON object per line with the existing target keys. Open it in binary-compatible mode before passing it to BigQuery. Always close and delete temporary files, including on validation, load, archive, or retry failures.

Streaming bounds memory, not disk. Use a dedicated writable temporary directory such as `/var/tmp/jobs-orchestrator`, document that transformed disk usage is proportional to source size, and provision enough free space for the largest expected source plus transformation overhead. If the available space is insufficient, treat that as an operational failure rather than silently truncating or partially loading a file.

### 4. Implement generation-safe lifecycle movement

GCS has no atomic rename. Implement a move as copy followed by delete:

Before processing each run, check for objects named exactly `<archive-prefix>/` and `<reject-prefix>/` and upload empty marker objects when absent. Never create `<incoming-prefix>/`; incoming remains producer-managed. Treat marker creation errors as transient GCS failures under the standard retry policy. Marker creation is for console visibility only—GCS does not require a real folder before writing objects beneath a prefix.

1. reference the exact generation supplied by the sensor;
2. fail the stale run without touching a newer generation if that exact observed generation no longer exists;
3. copy it to archive or reject using the source generation and a source-generation match precondition;
4. capture the returned destination generation;
5. for a reject, patch metadata on that exact destination generation using an appropriate destination metageneration precondition;
6. allow the destination name to be overwritten;
7. verify the copy and metadata calls succeed;
8. delete only the exact source generation using `if_generation_match`;
9. never delete a newer upload that reused the same object name.

For rejected objects, set concise custom metadata such as:

```text
dagster_reject_category=<short stable category>
dagster_rejected_at=<UTC timestamp>
```

Detailed exception text and stack traces belong in Dagster logs rather than object metadata.

If rejection itself fails, leave the incoming object untouched, fail loudly, and rely on manual Dagster re-execution after the underlying GCS problem is corrected. Because destination overwrite creates a new current generation, older generations may remain when bucket versioning or soft-delete retention is enabled; this plan does not purge them.

### 5. Implement the `serpapi_load_jobs` asset

Create `jobs_orchestrator/assets/serpapi_load_jobs/asset.py` with:

- a typed per-run config containing `object_name` and `generation`;
- an unpartitioned asset named `serpapi_load_jobs`;
- an explicitly defined asset job used by the sensor;
- the custom GCP resource;
- run tags for `DAGSTER_ENVIRONMENT` and workload concurrency.

Asset behavior:

1. Log the source URI, generation, environment, and current attempt.
2. Reject unsupported file extensions immediately.
3. Open the exact observed generation.
4. stream-validate and transform into temporary JSONL;
5. rewind the temporary file;
6. pass a rewound binary file handle to `BigQuery Client.load_table_from_file` exactly once, using a `LoadJobConfig` with `source_format=NEWLINE_DELIMITED_JSON`, `write_disposition=WRITE_APPEND`, and `create_disposition=CREATE_NEVER`;
7. wait for `job.result()` and retain the load-job ID for logging;
8. move the source to archive;
9. emit a materialization result with basic metadata: source URI, archive URI, row count, BigQuery job ID, and attempt count.

The `gcs_uri` written into every row remains the original incoming URI, even after the object moves to archive.

Do not assign deterministic BigQuery job IDs or add merge logic: retry duplicates are allowed by design.

### 6. Implement retry and rejection control flow

Do not attach an asset/job retry policy and do not enable instance-level automatic run retries for this workload. Catch and classify failures around cloud operations, and explicitly raise Dagster `RetryRequested` only for transient failures.

- **Permanent input failures:** unsupported extension, invalid UTF-8/JSON, non-object JSON value, or zero records. Move to reject immediately and raise a Dagster failure without retry.
- **Permanent BigQuery request failures:** invalid schema/request responses should reject without retry.
- **Transient failures:** network timeouts and retryable GCS/BigQuery service responses should request a Dagster retry.
- **Unknown operational failures:** treat as transient until the final attempt unless clearly caused by input.

Implement exactly three total attempts:

1. initial attempt;
2. first retry after roughly 60 seconds plus small random jitter;
3. second retry after roughly 120 seconds plus small random jitter.

Use `context.retry_number` as the attempt source: values `0`, `1`, and `2` represent the three total Dagster attempts. On attempts 0 and 1, raise `RetryRequested(max_retries=2, seconds_to_wait=<jittered delay>)`. On attempt 2, do not request another retry; move the source to reject and report failure. Google client libraries may perform their own bounded request-level retries within one Dagster attempt; these do not count as additional Dagster attempts and must not be configured without a timeout.

If BigQuery succeeds but archive movement fails, retry the complete asset. This may append duplicate rows and is explicitly acceptable. If archive movement still fails on attempt 2, move the original incoming generation to reject and mark it with a distinct post-load/archive-failure category. If archive copy succeeded but source deletion failed, both archive and reject copies can exist after final handling; log that state explicitly rather than implying the file was never loaded.

### 7. Implement the four-hour GCS sensor

Create `jobs_orchestrator/assets/serpapi_load_jobs/sensor.py` with a standard polling sensor targeting the asset job.

Sensor requirements:

- `minimum_interval_seconds=14_400` (a minimum interval between evaluations, so actual timing may be later than exactly four hours);
- list recursively beneath the normalized incoming prefix with a trailing `/` so similarly named prefixes are excluded;
- ignore only directory placeholder objects;
- include unsupported files so the asset can move them to reject;
- sort by `time_created` and then object name for deterministic oldest-first order;
- compare current identities against the cursor and emit no more than ten previously unemitted run requests per evaluation;
- use a run key containing bucket, object name, and generation;
- pass object name and generation through typed run config;
- add tags for environment and `workload=serpapi_load_jobs`.

The generation is internal coordination data, not a permanent business deduplication key. Dagster run-key deduplication prevents repeated sensor evaluations from launching the same observed upload. A re-upload receives a new generation and therefore a new run key.

Do not simply yield the oldest ten objects on every tick: objects still queued or running would consume those ten positions and strand later backlog. Store the set of already emitted identities that are still present under the incoming prefix. On each evaluation:

1. list all current incoming identities;
2. intersect the cursor's emitted set with current identities, pruning objects that have moved out of incoming;
3. select up to ten oldest current identities not in that emitted set;
4. emit their run requests;
5. persist the pruned set plus newly emitted identities.

Do not use a timestamp-only high-water mark. Run keys remain the durable fallback against duplicate launches if cursor state is reset.

### 8. Register definitions and concurrency

Update `jobs_orchestrator/definitions.py` to explicitly register:

- the `serpapi_load_jobs` asset;
- its asset job;
- its GCS polling sensor;
- the GCP resource.

Avoid implicit recursive discovery. Explicit imports make future per-asset folders predictable.

Configure the SQLite-backed Dagster instance's queued run coordinator with a tag concurrency limit of one for `workload=serpapi_load_jobs`. This allows the sensor to queue up to ten files while executing them strictly one at a time. Do not set a global one-run limit that would unnecessarily block unrelated future assets.

### 9. Add local-development configuration and documentation

Add `.env.dev.example` containing placeholder/demo values for the complete environment contract. Update `.gitignore` so `.env.dev` cannot be committed.

Update the orchestrator README with:

- Python environment creation and editable package installation;
- ADC login instructions;
- copying `.env.dev.example` to `.env.dev`;
- required demo bucket, producer-owned incoming prefix, automatically initialized archive/reject markers, and raw-table schema;
- `dagster dev` startup from `orchestration/jobs_orchestrator`;
- enabling/evaluating the sensor manually in the UI;
- warnings that the sensor normally polls only every four hours;
- basic re-execution instructions for a run whose reject move also failed.

Do not include real project IDs or credentials in the example file.

### 10. Add standalone Ubuntu deployment templates

Create `deploy/dagster.yaml.example`, to be installed as `$DAGSTER_HOME/dagster.yaml`, configured for:

- persistent SQLite storage rooted at `/var/lib/dagster/storage` for run history, event logs, and schedule/sensor state;
- local compute-log storage beneath `/var/lib/dagster/compute_logs`;
- `QueuedRunCoordinator`;
- `DefaultRunLauncher` so the daemon launches local subprocess runs;
- the workload tag concurrency limit of one.

SQLite is sufficient for this single-server, low-concurrency deployment. PostgreSQL migration and multi-instance shared storage are out of scope. Document that the SQLite directory must live on local persistent disk, must not be shared over a network filesystem, and should be backed up while Dagster services are stopped or through a SQLite-safe backup procedure.

Create `deploy/workspace.yaml.example` pointing to a local gRPC code server.

Create three `systemd` unit templates:

1. `jobs-orchestrator-code.service`
   - run `dagster code-server start` against `jobs_orchestrator.definitions`;
   - bind the gRPC server to `127.0.0.1:4000`;
   - restart on failure.
2. `jobs-orchestrator-daemon.service`
   - run `dagster-daemon run` against the shared workspace;
   - start after networking and the code server;
   - restart on failure.
3. `jobs-orchestrator-webserver.service`
   - run `dagster-webserver` against the shared workspace;
   - bind to `127.0.0.1:3000` by default so it is not exposed publicly;
   - restart on failure.

All units should:

- run as the dedicated `dagster` user;
- use the same `DAGSTER_HOME=/var/lib/dagster`;
- use `/opt/jobs-data-platform/.venv`;
- use the orchestrator directory as the working directory;
- load `/etc/jobs-orchestrator/environment`;
- ensure the daemon and every subprocess launched by `DefaultRunLauncher` inherit the same environment and credential path;
- avoid embedding passwords or credentials;
- use explicit executable paths;
- have clear service dependencies and restart policies.

Document, but do not automate, these server setup steps:

1. verify the existing Python 3.11 and Dagster installation and confirm its version is compatible with the pinned project dependencies;
2. create the `dagster` Linux user;
3. check out the repository beneath `/opt/jobs-data-platform`;
4. reuse the existing dedicated virtual environment if it is compatible, or create `/opt/jobs-data-platform/.venv` only if isolation is still needed; install the orchestrator project and point the unit templates at the selected environment's explicit executable paths;
5. create `/var/lib/dagster/storage`, `/var/lib/dagster/compute_logs`, and `/etc/jobs-orchestrator` with restrictive ownership and permissions;
6. install `dagster.yaml`, `workspace.yaml`, the environment file, and the service-account credential outside Git;
7. install, enable, and start the three units;
8. access the localhost-bound webserver through an SSH tunnel unless a separately secured reverse proxy is introduced;
9. establish a SQLite-safe backup procedure for `/var/lib/dagster/storage`.

Do not add container or reverse-proxy implementation to this plan.

Document the service account's required permissions without provisioning them automatically:

- GCS `storage.objects.list`, `storage.objects.get`, `storage.objects.create`, `storage.objects.delete`, and `storage.objects.update` on the configured bucket (a narrowly scoped custom role or bucket-level role may provide these);
- project-level `bigquery.jobs.create`;
- destination-table/dataset permissions for `bigquery.tables.get` and `bigquery.tables.updateData`;
- credential-file ownership by the `dagster` user and mode `0600` or stricter.

## Manual Verification

No automated tests are required for this project. Complete the following manual checks using the demo project before considering the implementation ready:

1. **Definition loading**
   - Start with `DAGSTER_ENVIRONMENT=dev dagster dev`, allowing the process to load `.env.dev`.
   - Confirm the asset, asset job, sensor, and GCP resource load without definition errors.
   - Confirm the first asset run creates archive and reject marker objects when they are absent and does not create the incoming marker.
2. **Valid file**
   - Upload a small valid JSONL object beneath the demo incoming prefix.
   - Evaluate the sensor manually rather than waiting four hours.
   - Confirm exactly one run request is created for that generation.
   - Confirm the expected row count appends to the demo raw table.
   - Confirm the source moves to the matching archive relative path.
   - Confirm the run logs show filename, row count, source/archive path, and outcome.
3. **Repeated sensor evaluation**
   - Evaluate the sensor again before processing or while the run is queued.
   - Confirm the deterministic run key prevents a second run for the same generation.
4. **Same-name re-upload**
   - Upload a new object at the same incoming name after the first is archived.
   - Confirm its new generation creates another run and the archive destination is overwritten.
5. **Reject behavior**
   - Manually try malformed, empty, and unsupported files.
   - Confirm each moves to the matching reject path with concise reason/timestamp metadata and does not append rows.
6. **One-file load behavior**
   - Confirm the Dagster logs show one BigQuery load-job ID for each valid source file.
7. **Sequential execution**
   - Queue more than one file and confirm only one workload run executes at a time.
8. **Server operation**
   - Confirm all three `systemd` units run under the `dagster` user.
   - Restart the server or services and confirm SQLite-backed run/sensor history remains available.
   - Confirm the daemon can evaluate the sensor after restart.

Do not point manual smoke tests at production resources.

## Definition of Done

The project is complete when:

- the Dagster definitions load from the reorganized asset package;
- the demo sensor discovers incoming objects every four hours and deduplicates repeated observations by generation-aware run key;
- at most ten runs are queued per tick and at most one loader run executes concurrently;
- valid JSONL objects are fully validated, transformed, and appended through one BigQuery load job;
- successful objects move to archive using generation-safe copy/delete behavior;
- archive and reject marker objects are created idempotently by the asset while incoming remains producer-managed;
- invalid or exhausted-retry objects move to reject with concise metadata;
- empty and unsupported objects are rejected;
- retryable failures receive three total attempts with the agreed delays;
- the raw BigQuery schema and row mapping remain compatible with existing dbt models;
- the Dagster implementation performs no load-ledger reads or writes;
- demo smoke verification succeeds;
- SQLite-backed webserver, daemon, and code server can run as standalone Ubuntu `systemd` services;
- deployment documentation contains no secrets;
- legacy loader code and production scheduling remain untouched.

## Implementation Order

Execute the work in this dependency order:

1. pin dependencies and create the package folders;
2. implement environment/resource validation;
3. implement JSONL transformation and GCS lifecycle helpers;
4. implement the asset and retry behavior;
5. implement the sensor and asset job;
6. register definitions and configure queued-run concurrency;
7. add local development examples and documentation;
8. manually validate against the demo project;
9. add SQLite/Dagster instance templates and `systemd` units;
10. install and verify the standalone Ubuntu services.

Stop after the standalone Dagster version is working. Begin production cutover only under a separately reviewed plan.
