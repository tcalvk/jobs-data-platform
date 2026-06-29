# Groq Skills Enrichment Low-Complexity Migration Plan

## Goal

Migrate the `enrich_skills` job to Groq's replacement model with minimal code complexity while reducing the chance of exceeding the new per-key rate limits.

This plan covers items **1, 3, and 4** from the low-complexity recommendation, plus one small resilience improvement:

1. Lower daily max jobs from `350` to `300`.
3. Make the Groq model configurable.
4. Reduce default retries from `5` to `2`.
5. Batch BigQuery writes every `50` successful enrichments.

Item 2 from the recommendation, lowering effective RPM per key, is intentionally out of scope for this plan.

## Context

The skills enrichment implementation lives in:

```text
dags/ao/enrich_skills.py
```

Current relevant behavior:

- The Groq model is hardcoded as `llama-3.1-8b-instant`.
- The default daily job limit is `350` via `ENRICH_SKILLS_DAILY_MAX_JOBS` fallback.
- The default retry count is `5` via `GROQ_MAX_RETRIES` fallback.
- Enriched rows are uploaded to BigQuery only once, at the end of the run.
- Two Groq API keys are used and have independent limits.
- Observed average usage is approximately `176k tokens/day/key`.

New Groq limits per API key:

| Limit | Value |
|---|---:|
| Requests per minute | 30 |
| Requests per day | 1,000 |
| Tokens per minute | 8,000 |
| Tokens per day | 200,000 |

Reducing daily jobs from `350` to `300` estimates token usage at:

```text
176k * 300 / 350 ≈ 151k tokens/key/day
```

This creates meaningful buffer under the new `200k tokens/day/key` limit without introducing token accounting or more complex rate-limit logic.

## Scope

Implement only these changes:

1. Change the default daily max jobs from `350` to `300`.
2. Make the Groq model ID configurable with `GROQ_MODEL_ID`.
3. Change the default Groq retry count from `5` to `2`.
4. Upload enriched rows to BigQuery in batches of `50`.

Do not add the following in this migration:

- token tracking
- request-per-day tracking
- token-per-minute pacing
- description truncation
- new key-balancing logic
- new rate-limit abstractions

## Implementation Steps

### 1. Lower Default Daily Max Jobs

File:

```text
dags/ao/enrich_skills.py
```

Find:

```python
daily_max_jobs = int(os.environ.get("ENRICH_SKILLS_DAILY_MAX_JOBS", "350"))
```

Change to:

```python
daily_max_jobs = int(os.environ.get("ENRICH_SKILLS_DAILY_MAX_JOBS", "300"))
```

Rationale:

- Keeps the existing env var override behavior.
- Makes the safe migration value the default.
- Reduces expected daily token usage by about 14%.

### 2. Make Groq Model Configurable

File:

```text
dags/ao/enrich_skills.py
```

Find near the top of the file:

```python
MODEL_ID = "llama-3.1-8b-instant"
```

Change to:

```python
MODEL_ID = os.environ.get("GROQ_MODEL_ID", "llama-3.1-8b-instant")
```

Rationale:

- Allows the production model to be changed through Cloud Run Job environment configuration.
- Avoids another code deploy if Groq changes model IDs again.
- Keeps local/dev behavior backward compatible when `GROQ_MODEL_ID` is unset.

### 3. Reduce Default Retry Count

File:

```text
dags/ao/enrich_skills.py
```

Find:

```python
max_retries = int(os.environ.get("GROQ_MAX_RETRIES", "5"))
```

Change to:

```python
max_retries = int(os.environ.get("GROQ_MAX_RETRIES", "2"))
```

Rationale:

- Retries consume request and token budget.
- The new limits make excessive retries more expensive.
- A default of `2` still allows recovery from transient failures while limiting budget waste.

### 4. Batch BigQuery Writes Every 50 Rows

File:

```text
dags/ao/enrich_skills.py
```

Add a batch-size setting in `main()` near the other runtime settings:

```python
upload_batch_size = int(os.environ.get("ENRICH_SKILLS_UPLOAD_BATCH_SIZE", "50"))
```

Current behavior accumulates all successful enrichments in `enriched_rows` and uploads once after the processing loop:

```python
_upload_skills(bq_client, enriched_rows, target_table_id)
print(f"Uploaded {len(enriched_rows)} rows to {target_table_id}")
```

Change the loop so that after each successful enrichment, if `len(enriched_rows) >= upload_batch_size`, it uploads the current batch and clears the list.

Suggested implementation pattern:

```python
total_uploaded = 0

for idx, row in enumerate(jobs, start=1):
    ...
    try:
        skills, next_key_index = _extract_skills_with_retries(...)
        enriched_rows.append(
            {
                "job_id": job_id,
                "data_source": data_source,
                "skills": skills,
                "created_at": _now_utc(),
            }
        )

        if len(enriched_rows) >= upload_batch_size:
            _upload_skills(bq_client, enriched_rows, target_table_id)
            total_uploaded += len(enriched_rows)
            print(f"Uploaded batch of {len(enriched_rows)} rows to {target_table_id}")
            enriched_rows.clear()
    except Exception as exc:
        ...

_upload_skills(bq_client, enriched_rows, target_table_id)
total_uploaded += len(enriched_rows)
print(f"Uploaded {total_uploaded} total rows to {target_table_id}")
```

Important implementation notes:

- Keep `_upload_skills()` unchanged unless necessary.
- Upload only after successful enrichments are appended.
- Clear `enriched_rows` only after `_upload_skills()` succeeds.
- Keep the final upload after the loop so the last partial batch is written.
- Track `total_uploaded` separately because `len(enriched_rows)` will only represent the current pending batch after this change.
- Keep the existing `failed` tracking unchanged.

Rationale:

- If the job later runs out of tokens, receives repeated rate limits, times out, or exits unexpectedly, previously uploaded batches are preserved.
- This avoids re-enriching already successful jobs on the next run and wasting token budget.
- A batch size of `50` keeps BigQuery load jobs reasonably low while limiting possible lost work to at most the current in-memory batch.

## Deployment Configuration

Set the new model in the Cloud Run Job environment:

```text
GROQ_MODEL_ID=<new-groq-model-id>
```

Recommended explicit settings, even though code defaults will cover them:

```text
ENRICH_SKILLS_DAILY_MAX_JOBS=300
GROQ_MAX_RETRIES=2
ENRICH_SKILLS_UPLOAD_BATCH_SIZE=50
```

Do not change the Groq API key env vars as part of this plan:

```text
GROQ_API_KEY_ICLOUD
GROQ_API_KEY_GOOGLE
```

## Verification Plan

### Static Check

From repo root, run:

```bash
python -m py_compile dags/ao/enrich_skills.py
```

### Optional Smoke Test

Only run this if BigQuery and Groq credentials are available in the environment:

```bash
ENRICH_SKILLS_DAILY_MAX_JOBS=1 python controller.py enrich_skills
```

Required env vars for the smoke test:

```text
BQ_JOBS_DIM_TABLE_ID
GROQ_API_KEY_ICLOUD
GROQ_API_KEY_GOOGLE
BQ_PROJECT_ID or GOOGLE_CLOUD_PROJECT or GCP_PROJECT
GROQ_MODEL_ID
```

Expected smoke-test result:

- The job starts successfully.
- It finds at most one unenriched job.
- It calls the configured Groq model.
- It uploads one enrichment row, or logs that no jobs need enrichment.

### Optional Batch Upload Smoke Test

If credentials are available and there are enough unenriched jobs, run a small batch-size test:

```bash
ENRICH_SKILLS_DAILY_MAX_JOBS=3 ENRICH_SKILLS_UPLOAD_BATCH_SIZE=2 python controller.py enrich_skills
```

Expected result:

- One batch upload occurs after 2 successful rows.
- The final partial batch uploads after the loop.
- The final log reports the total uploaded row count.

## Rollout Plan

1. Implement the four code changes in `dags/ao/enrich_skills.py`.
2. Run the static check.
3. Optionally run the one-job smoke test if credentials are available.
4. Deploy the Cloud Run Job with `GROQ_MODEL_ID` set to the replacement model.
5. Keep daily max at `300` for the first 3 to 5 daily runs.
6. Monitor Groq token usage per key.
7. If usage stays below approximately `170k tokens/key/day`, consider increasing `ENRICH_SKILLS_DAILY_MAX_JOBS` to `325`.
8. If usage stays below approximately `180k tokens/key/day`, consider returning to `350`.

## Success Criteria

- `dags/ao/enrich_skills.py` compiles successfully.
- The enrichment job uses the model from `GROQ_MODEL_ID` when provided.
- Default daily max is `300` when `ENRICH_SKILLS_DAILY_MAX_JOBS` is unset.
- Default max retries is `2` when `GROQ_MAX_RETRIES` is unset.
- Enriched rows are uploaded in batches of `50` by default.
- Daily production runs complete without exceeding Groq's new per-key token limit.
- If a run exits before all selected jobs are processed, successfully uploaded batches are not lost.

## Future Hardening Ideas

These are intentionally not part of this low-complexity migration, but may be useful later:

- Track actual `completion.usage.total_tokens` per key.
- Stop using a key near a daily token target.
- Add description truncation for unusually long job descriptions.
- Make RPM configurable by env var.
- Use Groq rate-limit reset headers proactively.
