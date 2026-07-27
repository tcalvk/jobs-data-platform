# Dagster `serpapi_load_jobs` Production Cutover Plan

## Goal

Migrate production SerpApi JSONL loading from the legacy Cloud Run
`gcs_to_bq_load` task to the self-hosted Dagster `serpapi_load_jobs` asset on a
standalone Ubuntu server, without dual-loading objects or losing producer
output.

The recommended cutover uses a short producer pause. The legacy loader gets one
final drain, is disabled, and only then is the producer routed to the new
`serpapi/incoming/` lifecycle. The Dagster sensor must never overlap with a
legacy loader that recursively scans the broader `serpapi/` prefix.

## Scope

### In scope

- Production readiness fixes for the Dagster loader and downstream data path.
- Inventory and preservation of current Cloud Run and Cloud Scheduler settings.
- Ubuntu host preparation, deployment, credentials, SQLite state, and
  `systemd` operation.
- Production GCS prefix and producer configuration migration.
- A controlled handoff from the legacy loader to Dagster.
- Validation, monitoring, rollback, and eventual legacy retirement.

### Out of scope

- Migrating the SerpApi producer away from Cloud Run.
- Containerizing Dagster or introducing a multi-node Dagster deployment.
- Automatically provisioning production buckets, BigQuery tables, or IAM.
- Deleting legacy jobs, schedules, ledger data, or historical GCS objects during
  the initial cutover.

## Known Current State

- Dagster polls `GCS_INCOMING_PREFIX` every four hours, emits at most ten new
  object generations per tick, and relies on a queued-run tag limit to execute
  one loader run at a time.
- The producer builds names as
  `<GCS_PREFIX>/<SOURCE_NAME>/<query_id>/<timestamp>.jsonl`. With
  `GCS_PREFIX=serpapi/incoming` and the default `SOURCE_NAME=serpapi`, the
  resulting path is
  `serpapi/incoming/serpapi/<query_id>/<timestamp>.jsonl`. This is supported;
  the extra `serpapi/` path component should be accepted or deliberately
  changed before cutover.
- The legacy loader recursively scans its configured prefix, which defaults to
  `serpapi`. If left active, it can see new incoming, archive, and reject paths.
- The legacy loader leaves source objects in place and uses a BigQuery ledger;
  Dagster moves objects and does not use that ledger.
- Dagster delivery is at-least-once. A BigQuery success followed by an archive
  failure can append duplicate rows on retry.
- Current staging and intermediate dbt models do not deduplicate retry copies.
  `dim_job_listings` deduplicates, but `fact_scraped_jobs` does not and may fail
  its `(job_id, created_at_utc)` uniqueness expectation.
- The production Cloud Run Job and Cloud Scheduler resource definitions are not
  stored in this repository. Their live configuration must be inventoried from
  GCP before changes are made.
- The Dagster implementation and deployment files must be committed, reviewed,
  merged, and deployed from an immutable commit before production use. Never
  deploy the current working tree directly.

## Cutover Principles

1. **Never dual-run the loaders.** The legacy loader must be stopped before any
   producer output is written beneath the Dagster lifecycle prefix.
2. **Pause writes to establish a boundary.** Pause the producer while the final
   legacy load runs and configuration is switched.
3. **Do not migrate historical legacy objects into incoming.** Historical files
   already covered by the ledger remain in their existing location. Copying
   them into incoming would make Dagster load them again.
4. **Do not delete rollback assets during stabilization.** Retain the legacy
   Cloud Run Job, scheduler configuration export, ledger, and historical files
   until the acceptance window closes.
5. **Roll back to an isolated prefix.** After lifecycle objects exist, do not
   re-enable a legacy loader scoped broadly to `serpapi/`; it could ingest
   archive and reject files.
6. **Use explicit go/no-go gates.** Every phase below must have evidence and an
   owner before the next phase begins.

## Required Decisions

Record these in the cutover ticket before implementation begins:

| Decision | Required value |
|---|---|
| Producer Cloud Run project and region | TBD |
| Loader Cloud Run project and region | TBD |
| Producer Scheduler project and location | TBD; may differ from Cloud Run |
| Loader Scheduler project and location | TBD; may differ from Cloud Run |
| Production bucket | TBD |
| BigQuery raw table | TBD (`project.dataset.table`) |
| Producer Cloud Run Job and Scheduler names | TBD |
| Legacy loader Cloud Run Job and Scheduler names | TBD |
| Current producer and loader prefixes | TBD from live configuration |
| Final incoming/archive/reject prefixes | Recommended `serpapi/incoming`, `serpapi/archive`, `serpapi/reject` |
| Whether to retain the extra `incoming/serpapi/` path component | TBD |
| Expected objects/day and maximum object size | TBD from production history |
| Same-name archive/reject recovery | Require versioning/retention or generation-qualified destinations |
| Maximum acceptable incoming age | TBD |
| Stabilization period before retirement | Recommended 7 days minimum |
| Cutover owner, data validator, and rollback approver | TBD |
| Maintenance window | TBD |

## Phase 0: Production Readiness Blockers

Complete these before provisioning or cutover.

### 0.1 Release the implementation

- Commit all intended Dagster implementation, dependency, documentation, and
  deployment-template changes.
- Exclude unrelated local files, generated bytecode, credentials, `.env.dev`,
  keys, logs, and Dagster state.
- Review and merge through the normal repository process.
- Record the production commit SHA and, if used by the project, create a release
  tag.
- Confirm a clean checkout at that SHA can install the orchestrator and load
  `jobs_orchestrator.definitions`.

**Gate:** production deployment identifies an immutable reviewed commit.

### 0.2 Correct loader safety behavior

Before production, add focused verification and fix any failures for these
cases:

- Reject overlapping lifecycle prefixes, not only equal prefixes. For example,
  `incoming=serpapi` and `archive=serpapi/archive` must be invalid.
- A stale GCS generation must fail without retrying or touching a newer upload.
  Ensure a Dagster `Failure` raised for a stale source is not caught and treated
  as an unknown transient error by the outer exception handler.
- IAM failures, missing infrastructure, and credential/configuration errors
  must not cause a valid source file to be moved to reject. These are
  operational failures; leave the exact incoming generation available for
  repair and re-execution.
- Preserve immediate rejection for actual input failures such as invalid UTF-8,
  malformed JSON, non-object JSON, empty files, and unsupported extensions.
- Verify BigQuery timeouts and retry behavior, especially the possibility that
  a server-side job completes after the local wait times out.
- Verify generation preconditions for source read, copy, metadata update, and
  deletion against the production library versions.
- Decide how same-name re-uploads remain independently recoverable. Either
  include the source generation in archive/reject destination names or require
  bucket versioning/soft-delete retention and prove operators can trace every
  destination generation back to its source run.

At minimum, exercise these with targeted automated tests or a production-like
test bucket/table before approving the release.

**Gate:** code review and test evidence show operational faults do not discard
valid input and stale runs cannot affect newer generations.

### 0.3 Resolve at-least-once duplicates

The implementation assumes downstream dbt owns deduplication, but the current
fact path does not fully do so. Exact retry deduplication is not possible from
the current four raw columns alone: `gcs_uri` does not include GCS generation or
line ordinal, and a content fingerprint could incorrectly collapse legitimate
identical lines. Choose and implement one reviewed approach before cutover:

1. **Recommended:** make the BigQuery load submission idempotent for the exact
   `(bucket, object name, generation)` using a deterministic BigQuery job ID.
   On retry, retrieve and inspect the existing job rather than submitting a
   second append. Explicitly test conflict, timeout, completed-job, failed-job,
   and archive-failure behavior.
2. Persist immutable source generation and record ordinal in an ingestion
   manifest or expanded raw contract, then deduplicate only exact retry copies.
3. Add a loader ledger keyed by object generation with a separately reviewed
   design that accounts for failure between the BigQuery job and ledger write.
4. Explicitly accept duplicate facts and uniqueness-test failures, with a
   documented cleanup process. This is not recommended for production.

Run focused dbt models/tests and determine whether a full refresh or expanded
partition window is needed. Dagster processes oldest objects first; any backlog
whose `fetched_at` is outside the current incremental lookback can otherwise be
missed downstream.

**Gate:** forced retry duplicates do not produce duplicate reporting facts or
failed uniqueness tests.

### 0.4 Validate production throughput

- Measure producer objects per day and peak objects per four-hour interval.
- Compare the result with the current maximum of 10 emissions per tick, or about
  60 per day under ideal six-tick operation.
- Measure largest source size and transformation expansion.
- Measure sequential completed runs/hour, including normal run duration,
  request retries, Dagster retries, and expected host downtime.
- If arrival rate can exceed drain rate, adjust sensor interval/run limit or
  redesign capacity before cutover. Preserve one-at-a-time execution unless
  parallel safety is separately validated.
- Define backlog alerts using count and age of objects under incoming.

**Gate:** expected arrival rate remains below both sensor emission capacity and
measured sequential completion capacity with documented headroom, and the
largest expected backlog has an acceptable maximum drain time.

## Phase 1: Inventory Live Production

The exact commands depend on each resource's project and location. Capture outputs
in a restricted cutover evidence location; do not commit secrets.

1. Identify all relevant Cloud Run Jobs and Scheduler Jobs:

   ```bash
   gcloud run jobs list --project <run-project> --region <run-region>
   gcloud scheduler jobs list --project <scheduler-project> --location <scheduler-location>
   ```

2. Export/describe the producer and legacy loader jobs:

   ```bash
   gcloud run jobs describe <producer-job> --project <producer-run-project> --region <producer-run-region> --format=export
   gcloud run jobs describe <loader-job> --project <loader-run-project> --region <loader-run-region> --format=export
   gcloud scheduler jobs describe <producer-scheduler> --project <producer-scheduler-project> --location <producer-scheduler-location>
   gcloud scheduler jobs describe <loader-scheduler> --project <loader-scheduler-project> --location <loader-scheduler-location>
   ```

3. Record for both jobs:
   - image digest/tag, command, arguments or `JOB_TASK`;
   - environment variables and secrets references;
   - service accounts, region, timeout, retries, task count, and parallelism;
   - scheduler cron, timezone, retry policy, invoker identity, and current state;
   - latest executions and whether one is currently running.
   - every invocation path, including Scheduler retries, manual operators,
     workflows, scripts, and service accounts that can start executions.
4. Confirm current values for `GCS_BUCKET`, `GCS_PREFIX`, `SOURCE_NAME`,
   `BQ_RAW_TABLE_ID`, and `BQ_LOAD_LEDGER_ID`.
5. Capture a generation manifest containing bucket, object name, generation,
   size, checksum, creation time, and legacy-ledger status. Measure existing
   legacy objects and reconcile the loader ledger sufficiently
   to identify unprocessed files. Do not infer backlog merely from files being
   present, because the legacy loader intentionally leaves processed files.
6. Record bucket versioning, soft-delete, retention, lifecycle, and object
   notification policies.
7. Capture the raw table schema, row count baseline, recent rows, and source
   freshness baseline.
8. Define a quarantine prefix outside both the legacy scan root and all Dagster
   lifecycle prefixes. Preserve generation/checksum and a loaded/not-loaded
   disposition for every quarantined object.
9. Create an approved pre-cutover BigQuery snapshot/clone or equivalent recovery
   point. Record expiration, owner, and the exact row-removal/restoration and dbt
   rebuild procedure for cutover generations.

**Gate:** the team can restore every changed Cloud Run/Scheduler setting and can
identify active executions and unprocessed legacy files.

## Phase 2: Prepare the Ubuntu Server

### 2.1 Host requirements

- Use a stable Ubuntu host with reliable power, network, time synchronization,
  SSH access, and a documented reboot owner.
- Install security updates and Python 3.11.
- Reserve local persistent disk for:
  - `/var/lib/dagster/storage` (SQLite state);
  - `/var/lib/dagster/compute_logs`;
  - `/var/tmp/jobs-orchestrator` (one transformed file proportional to the
    largest source plus overhead).
- Define disk thresholds and log retention before starting production.
- Do not place SQLite on iCloud, NFS, SMB, or another network filesystem.

### 2.2 User, checkout, and virtual environment

- Create the dedicated non-login `dagster` user/group.
- Deploy the approved commit to an immutable versioned release directory, such
  as `/opt/jobs-data-platform/releases/<commit-sha>`, and point an atomic
  `/opt/jobs-data-platform/current` symlink at it.
- Create a separate Python 3.11 virtual environment for that release, or use a
  versioned shared environment whose exact package set is immutable.
- Install the orchestrator project from the checkout so the pinned Dagster,
  webserver, Google clients, and dotenv packages are present.
- Record output from Python and Dagster version checks.
- Precreate `/var/tmp/jobs-orchestrator` with restrictive ownership for the
  `dagster` user.
- Retain the previous release and environment. Document service stop, symlink
  switch, SQLite compatibility check/restore, and service start order for
  application rollback.

### 2.3 Dagster state and services

- Create `/var/lib/dagster/storage` and `/var/lib/dagster/compute_logs`, owned by
  `dagster` with restrictive permissions.
- Install `deploy/dagster.yaml.example` as
  `/var/lib/dagster/dagster.yaml` and verify:
  - persistent SQLite storage;
  - local compute logs;
  - `QueuedRunCoordinator`;
  - `DefaultRunLauncher`;
  - tag concurrency limit 1 for `workload=serpapi_load_jobs`.
- Install `workspace.yaml` and all three `systemd` units.
- Add reasonable service hardening (`UMask`, `NoNewPrivileges`, restricted
  writable paths, and resource limits) without preventing subprocess runs or
  access to credentials, state, logs, and temporary storage.
- Keep gRPC and webserver bound to localhost. Access the UI through an SSH
  tunnel or a separately approved authenticated reverse proxy.
- Start the code server, daemon, and webserver with the production sensor still
  stopped.
- Inspect `systemctl cat/show` and verify all three services use the same
  `DAGSTER_HOME`, environment file, working directory/current release,
  credential path, and explicit executable paths. Launch a real run as the
  `dagster` user to prove `DefaultRunLauncher` children inherit them.
- Reboot once and prove all services and Dagster state return successfully.

### 2.4 SQLite backup and restore

- Establish an automated SQLite-safe, encrypted off-host backup with defined
  RPO, RTO, retention, and integrity checks.
- Back up while services are stopped or use SQLite's supported online backup
  mechanism; do not copy active database files naively.
- Include `dagster.yaml`, `workspace.yaml`, installed commit SHA, and non-secret
  environment metadata in the recovery documentation.
- Perform one restore rehearsal before cutover and confirm run history and
  sensor state remain visible. Before restarting the daemon after a restore,
  inventory and cancel or explicitly approve restored queued runs so old work
  does not resume unexpectedly.

**Gate:** a reboot and backup/restore rehearsal preserve the Dagster instance,
and only one workload run can execute at a time.

## Phase 3: Production Identity and Configuration

### 3.1 Service account

Create or select a dedicated least-privilege identity with:

- GCS object list/get/create/delete/update permissions scoped to the production
  bucket;
- `bigquery.jobs.create` in the project;
- `bigquery.tables.get` and `bigquery.tables.updateData` on the destination.

Store the service-account JSON outside Git, owned by `dagster`, mode `0600` or
stricter. Document issuance and rotation. If a keyless approach is available to
the Ubuntu host, prefer it under a separately reviewed authentication setup.

### 3.2 Server environment

Create `/etc/jobs-orchestrator/environment` with restrictive permissions:

```text
DAGSTER_ENVIRONMENT=prod
GCP_PROJECT_ID=<production-project>
GCS_BUCKET=<production-bucket>
GCS_INCOMING_PREFIX=serpapi/incoming
GCS_ARCHIVE_PREFIX=serpapi/archive
GCS_REJECT_PREFIX=serpapi/reject
BQ_RAW_TABLE_ID=<production-project>.<dataset>.<table>
GOOGLE_APPLICATION_CREDENTIALS=<absolute-server-key-path>
PRODUCTION_GCP_PROJECT_ID=<production-project>
PRODUCTION_GCS_BUCKET=<production-bucket>
```

Do not use `.env.dev` on the server. Confirm the definitions load under the
`dagster` user without changing bucket/table contents.

### 3.3 Prefix and resource checks

- Confirm the three prefixes are nonempty, pairwise distinct, and neither equal
  nor ancestors/descendants of each other.
- Confirm the bucket and destination table already exist.
- Confirm the raw table schema is exactly compatible with:

  ```sql
  created_at TIMESTAMP,
  job_data JSON,
  query_version_id INT64,
  gcs_uri STRING
  ```
- Record field modes, partitioning, clustering, table expiration, and relevant
  constraints in addition to column names/types. Confirm the load job uses
  append, never creates the table, and rejects bad records as intended.
- Confirm the incoming prefix contains no historical files before producer
  routing changes. If it does, inventory each generation and decide explicitly
  whether it is new, already loaded, or quarantined.
- Exercise identity read/list and BigQuery table inspection from the server.
- Use a separate canary bucket/table or an approved synthetic production record
  to validate write, copy, metadata-update, delete, and BigQuery-load
  permissions before the cutover window.
- If destination names can be overwritten, process two same-name source
  generations and prove both remain independently traceable and recoverable
  under the selected bucket retention/versioning design.

**Gate:** all production permissions work from the Ubuntu service identity and
the sensor remains disabled.

## Phase 4: Monitoring and Operations Readiness

Before cutover, assign an owner and alert path for:

- all three `systemd` services inactive or repeatedly restarting;
- no successful sensor evaluation within five hours;
- oldest incoming object beyond the agreed SLA;
- incoming count growing across two evaluations;
- any failed/retrying Dagster run;
- any object in reject;
- `/var/tmp`, Dagster state, or compute-log disk pressure;
- SQLite backup age/failure;
- BigQuery load errors and dbt source freshness/test failures.

Create an operator runbook covering:

- SSH tunnel and Dagster UI access;
- checking service/journal status;
- identifying the exact GCS generation for a run;
- re-executing after an operational failure;
- interpreting archive versus reject metadata;
- handling the ambiguous state where BigQuery may have succeeded before an
  archive failure or timeout;
- pausing the sensor and producer;
- restoring SQLite and credentials;
- contacting the cutover/data owner.

**Gate:** a named operator can diagnose a failed canary without developer
assistance.

## Phase 5: Pre-Cutover Rehearsal

Perform a rehearsal against isolated non-production resources using the same
Ubuntu services and service topology:

1. valid JSONL loads once and moves to the matching archive path;
2. malformed, empty, and unsupported objects move to reject with metadata;
3. repeated sensor evaluation does not launch the same generation twice;
4. same-name re-upload launches the new generation;
5. multiple objects queue but run sequentially;
6. process/service restart preserves cursor and run history;
7. forced archive failure demonstrates the expected at-least-once behavior and
   downstream deduplication;
8. stale generation and IAM/configuration failures leave newer/valid inputs
   safe;
9. restore from SQLite backup and verify no unexpected relaunches;
10. measure processing time and backlog drain rate.

Obtain explicit go/no-go approval from engineering, data, and operations.

## Phase 6: Cutover Runbook

Use one maintenance window with a shared timestamped log. Do not improvise the
order.

### T-24 hours

1. Freeze loader, producer-path, dbt-dedup, and Dagster deployment changes.
2. Confirm the Ubuntu host is healthy and running the approved commit.
3. Confirm services are active, the sensor is stopped, and the workload
   concurrency limit is loaded.
4. Confirm latest SQLite backup and sufficient disk space.
5. Confirm legacy and producer scheduler/job names, owners, and rollback
   commands from the live inventory.
6. Confirm no unrelated production maintenance overlaps the window.

### Establish the legacy/new boundary

1. **Pause both producer and legacy-loader Scheduler Jobs.** Record exact times
   and prior states.
2. Wait for every in-flight producer and loader Cloud Run execution to finish.
   Account for Scheduler retries and all other invocation paths identified in
   Phase 1. Temporarily remove other invokers if exclusivity cannot otherwise be
   proven.
3. Establish a fence and verify through execution history/audit logs that no
   producer or loader execution starts after it.
4. Capture a pre-drain object-generation manifest and ledger status.
5. Trigger exactly one uniquely identified final legacy loader execution using
   its existing production configuration.
6. Wait for completion and reconcile its logs, ledger changes, and any
   per-object errors. Remember that the legacy task can report overall success
   while logging individual object failures.
7. Capture a post-drain generation manifest. Assign every object to legacy
   loaded, Dagster eligible, external quarantine, or rollback handling based on
   generation and ledger status—not timestamp alone.
8. Resolve or move every unprocessed pre-cutover legacy generation to the
   external quarantine prefix with a named owner and deadline.
9. Record the cutover timestamp, manifests, and final legacy ledger/table
   baselines.
10. Verify both schedulers remain paused, no relevant Cloud Run execution is
    active, and no execution started after the fence except the unique final
    drain.

**No-go condition:** do not continue if the legacy backlog is unknown, either
job is still running, or the old loader cannot be proven inactive.

### Route new producer output

1. Update only the producer's GCS routing configuration to the approved new
   prefix, normally `GCS_PREFIX=serpapi/incoming`.
2. Keep the producer paused while describing/exporting its updated
   configuration and confirming unrelated values did not change.
3. Confirm the Dagster server uses matching `GCS_BUCKET` and
   `GCS_INCOMING_PREFIX` values.
4. Confirm incoming is empty at the boundary.
5. Keep the legacy loader disabled permanently throughout this step.

### Start Dagster ingestion

1. Enable `serpapi_load_jobs_sensor` in the production Dagster instance.
2. Keep the producer Scheduler paused and manually execute exactly one uniquely
   identified producer run.
3. Confirm output lands only beneath the approved incoming prefix.
4. Manually evaluate the sensor instead of waiting four hours.
5. Capture the complete generation manifest emitted by the manual producer
   execution, then observe every object in that canary batch end to end:
   - exact object generation in the run config;
   - one BigQuery load job;
   - expected row count;
   - source removed from incoming;
   - equivalent relative path present in archive;
   - no reject object;
   - materialization metadata and logs complete.
6. Re-evaluate the sensor and confirm the processed generation is not launched
   again.
7. Resume the producer's normal Scheduler Job only after every generation from
   the manual producer execution is reconciled. If the producer cannot emit a
   bounded canary batch, keep it paused until the entire execution is drained.
8. Leave the legacy loader scheduler paused.

### Validate the first production batch

- Reconcile each producer generation with one terminal Dagster outcome and one
  traceable archive/reject destination generation.
- Compare valid source line counts to the exact BigQuery job result and pre/post
  row baseline. Do not rely on `gcs_uri` alone to distinguish same-name source
  generations.
- Query retry-dedup keys and confirm no reporting duplicates.
- Run focused dbt models/tests with the partition window/full refresh selected
  in Phase 0.
- Confirm source freshness and key reporting outputs.
- Confirm incoming backlog count and oldest age are falling or stable.
- Confirm rejects are zero or understood.

**Go condition:** all producer output from the complete canary execution,
Dagster runs, destination generations, BigQuery jobs/rows, and downstream
models reconcile. Sampling alone is not sufficient unless its residual risk is
explicitly approved before the window.

## Phase 7: Stabilization

For at least seven days:

- review each sensor tick, run failure/retry, and reject;
- reconcile daily producer object count, Dagster materializations, archives,
  and raw-table row counts;
- monitor incoming count/age and verify capacity assumptions;
- verify daily dbt freshness and uniqueness/data-quality tests;
- confirm SQLite backups and disk thresholds;
- reboot or restart services once in an approved low-risk period to verify
  recovery;
- keep legacy scheduler disabled but retain its job, exported configuration,
  ledger, and historical source objects.

Exit stabilization only after no unexplained missing objects, rejects,
duplicates, or service/sensor gaps remain for the agreed period.

## Rollback Plan

### Rollback triggers

Pause migration immediately for any of these:

- objects are missing, loaded into the wrong table, or unexpectedly duplicated;
- legacy loader and Dagster overlap;
- valid files are moved to reject because of operational failures;
- incoming backlog age exceeds the agreed SLA and continues growing;
- server, network, credentials, SQLite, or sensor operation is unreliable;
- downstream dbt tests/reporting validation fail materially.

### Immediate containment

1. Pause the producer Scheduler Job, block the other invocation paths identified
   in Phase 1, and wait for or safely cancel active producer executions. Capture
   any partial output and verify through execution history/audit logs that no
   producer execution starts after the rollback fence.
2. Stop the Dagster sensor and then stop/suspend the daemon/run coordinator so a
   queued run cannot launch while containment is being established.
3. Inventory and cancel every queued/not-started run tagged
   `workload=serpapi_load_jobs`; stopping a sensor alone does not cancel runs it
   already emitted. Verify every workload run is terminal or explicitly
   approved to continue.
4. Manage any already-running subprocess separately. Let it finish only with
   explicit approval; otherwise terminate it and reconcile its BigQuery job
   state before retrying anything.
5. Confirm the legacy loader remains paused and its other invokers remain
   fenced.
6. Capture current incoming/archive/reject generations, Dagster run IDs,
   BigQuery job IDs, and raw-table baselines.
7. Do not copy files or rerun either loader until data state is reconciled.

If rows reached the wrong table or duplicate/partial data was materialized, use
the approved pre-cutover snapshot and per-generation BigQuery job manifest to
execute the reviewed row-removal/restoration procedure. Rebuild the dbt models
identified in Phase 1 and re-run their tests before declaring recovery. Never
delete rows using only a broad time range when exact cutover generations can be
identified.

### Preferred short outage recovery

Repair Dagster/server/configuration while producer writes are paused. Leave
incoming objects in place and manually re-execute only generations known not to
have completed, accounting for BigQuery jobs that may have succeeded before a
timeout or archive failure.

### Prolonged rollback to the legacy loader

Do **not** simply re-enable the old loader with `GCS_PREFIX=serpapi` after
archive/reject objects exist. Instead:

1. Select a fresh isolated top-level rollback prefix outside the Dagster
   lifecycle, such as `serpapi-legacy-rollback/<cutover-id>`.
2. Configure both producer and legacy loader to that exact isolated prefix.
3. Export and review both job configurations before resuming writes.
4. Keep all existing Dagster incoming/archive/reject objects frozen.
5. Resume producer and legacy loader only after confirming the legacy listing
   cannot include Dagster archive or reject paths.
6. Reconcile frozen Dagster objects separately. Never bulk-copy them to the
   rollback prefix without checking whether BigQuery already contains their
   rows.

Before ending the incident, assign every frozen generation one disposition and
deadline: proven already loaded, safely completed through Dagster, loaded once
through a controlled recovery path, or quarantined outside all scan roots with
a named owner. Include unresolved frozen objects in freshness/completeness
reporting until closed.

This rollback may create a new ledger namespace by object name. Preserve all
evidence needed to distinguish new rollback objects from previously loaded
Dagster objects.

## Phase 8: Legacy Retirement

After stabilization and explicit approval:

1. Keep an export of legacy Cloud Run/Scheduler configuration in the restricted
   operations archive.
2. Disable manual invocation permissions or clearly label the legacy job as
   retired so it cannot accidentally scan lifecycle paths.
3. Remove/delete the legacy Scheduler Job according to the team's retention
   process.
4. Decide separately when to delete the Cloud Run loader job. Do not remove
   `controller.py` or `dags/ao/gcs_to_bq_load.py` in the cutover commit unless a
   dedicated cleanup change is approved.
5. Retain the ledger read-only for the required audit period, then archive or
   delete it under a separate data-retention decision.
6. Define archive/reject object retention and lifecycle rules. Never delete
   rejects before investigation and retention requirements are satisfied.
7. Update the operational source of truth with the Dagster host, service owner,
   sensor cadence, IAM identity, backup procedure, and incident runbook.

## Evidence Checklist

- [ ] Approved production commit SHA
- [ ] Code-safety and duplicate-handling verification
- [ ] Throughput and disk-capacity calculation
- [ ] Exported producer/loader Cloud Run and Scheduler configurations
- [ ] Invocation-path inventory and execution fence procedure
- [ ] Pre/post-drain generation manifests and legacy ledger reconciliation
- [ ] BigQuery snapshot and tested data-restoration/dbt-rebuild procedure
- [ ] Ubuntu reboot and SQLite restore evidence
- [ ] Immutable release/application rollback rehearsal
- [ ] Service-account permission test
- [ ] Production environment and prefix review
- [ ] Monitoring ownership and alert tests
- [ ] Rehearsal results
- [ ] Final legacy load evidence and cutover timestamp
- [ ] First production object reconciliation
- [ ] Focused dbt run/test results
- [ ] Seven-day stabilization sign-off
- [ ] Legacy retirement approval

## Definition of Done

The migration is complete when:

- all new producer files land only beneath the approved incoming prefix;
- the legacy loader cannot run against Dagster incoming/archive/reject objects;
- each observed generation is processed by Dagster with one-at-a-time workload
  execution and expected retry behavior;
- successful files reach archive and failed input files reach reject with an
  understood reason;
- BigQuery and downstream dbt/reporting results reconcile without unexplained
  duplicates or missing historical partitions;
- Ubuntu services, SQLite restore, disk management, credentials, monitoring,
  and operator procedures have been proven;
- rollback can be executed without exposing lifecycle files to the broad legacy
  scanner;
- the stabilization period is complete and legacy scheduling is retired under
  explicit approval.
