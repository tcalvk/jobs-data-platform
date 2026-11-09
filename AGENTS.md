# AGENTS.md

## Repo shape
- `controller.py` is the Cloud Run job dispatcher; valid tasks are `serpapi_get_jobs`, `gcs_to_bq_load`, and `enrich_skills`.
- `dags/` contains plain Python job modules with `main()` functions, not Airflow DAG definitions.
- `dbt/` is a BigQuery dbt project (`jobs_data_platform`, profile `default`); layers are `staging` views and `int`/`marts`/`analysis`/`reporting` tables, with `exports` views.
- `jobs-evidence/` is a separate Evidence app; pages live in `jobs-evidence/pages/` and the main BigQuery source is `sources/project_portfolio`.
- The dbt project also has Tesla and personal-finance models; do not assume every dbt change is jobs-specific.

## Commands
- Python setup from repo root: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Run a job locally: `python controller.py serpapi_get_jobs`, `python controller.py gcs_to_bq_load`, `python controller.py enrich_skills`, or `JOB_TASK=serpapi_get_jobs python controller.py`.
- dbt deps/seed/run/test from repo root:
  - `dbt deps --project-dir dbt --profiles-dir dbt`
  - `dbt seed --project-dir dbt --profiles-dir dbt`
  - `DBT_GCP_PROJECT=<project-id> dbt run --select +tag:daily --project-dir dbt --profiles-dir dbt`
  - `DBT_GCP_PROJECT=<project-id> dbt test --project-dir dbt --profiles-dir dbt`
- Focus dbt work with `--select <model_or_tag>` on `dbt run`/`dbt test`; CI runs `deps -> seed -> run --select +tag:daily -> test`.
- Evidence app: `cd jobs-evidence && npm install`, then `npm run sources` before `npm run dev`, `npm run build`, or `npm run build:strict`.
- Container build source of truth is `cloudbuild.yaml`: `gcloud builds submit .`; the image tag is hard-coded to `v7`.

## Environment and auth gotchas
- Python jobs load `.env` only when `ENV` is unset or `ENV=local`; production should provide env vars directly.
- Local GCP auth is ADC/OAuth; GitHub Actions overwrites `dbt/profiles.yml` with service-account auth from `DBT_GCP_KEY`.
- dbt source databases default to `dev-projects-portfolio` unless `DBT_GCP_PROJECT` is set.
- Required task env vars:
  - `serpapi_get_jobs`: `GCS_BUCKET` plus `BQ_TABLE_ID` or `BQ_PROJECT_ID`/`GOOGLE_CLOUD_PROJECT`/`GCP_PROJECT`; it also needs one of those project variables to access the Secret Manager secret.
  - `gcs_to_bq_load`: `GCS_BUCKET`, `BQ_RAW_TABLE_ID`, `BQ_LOAD_LEDGER_ID`; `BQ_PROJECT_ID` is needed unless table IDs are fully qualified.
  - `enrich_skills`: `BQ_JOBS_DIM_TABLE_ID`, `GROQ_API_KEY_ICLOUD`, `GROQ_API_KEY_GOOGLE`, plus `BQ_PROJECT_ID`/`GOOGLE_CLOUD_PROJECT`/`GCP_PROJECT`.
- `serpapi_get_jobs` reads ordered SerpApi accounts from the `SERPAPI_ACCOUNTS` Google Secret Manager secret. Its value must be a JSON object with a non-empty `accounts` array whose objects have `api_key` and may have `name`; it does not read a local `SERPAPI_API_KEY` env var.
- `serpapi_get_jobs` test controls: `DRY_RUN=true` validates its normal configuration, Secret Manager accounts, and active BigQuery query rows, then exits without SerpApi requests or uploads. `MAX_QUERIES=N` processes only the first N active rows (ordered by `query_id`), and `TEST_MAX_JOBS=N` overrides each query's `max_jobs`; both N values must be positive integers. `DRY_RUN` accepts only `true` or `false` when set and takes precedence over processing controls.

## High-risk files and generated artifacts
- Do not print or modify `jobs-evidence/sources/project_portfolio/connection.options.yaml`; it may contain base64 service-account credentials.
- Treat `keys/`, `.env`, logs, `.venv`, `dbt/target/`, `dbt/dbt_packages/`, and Evidence generated/cache output as local artifacts.
- The README files are mostly starter-template prose; prefer executable configs and scripts over them.

## Verification notes
- There is no repo-level Python test or linter configured; use targeted job smoke runs only when the required cloud credentials/env are available.
- `Dockerfile.prod` has both `ENTRYPOINT ["python", "controller.py"]` and a non-task default `CMD`; pass an explicit task arg when running the image or Cloud Run Job.

## evidence.dev
### sources
Do not use tables in any other schema other than "reporting" for dashboard purposes. If you need to add logic to a report, you can create a semantic query in the /sources folder, otherwise, try to use the native source. 

### Standard Dashboard Elements
Some dashboard elements should always stay the same. Examples include: 
- Color palette
- Size, padding, width, etc. 
- Fonts
- Buttons (reset filters, more filters) 

#### Filters
Dashboard filters are generally considered standard. This means that if you add a filter to one dashboard, you typically want to add it to the others. Typically dashboard filters should also remain in the same standard order as well to ensure an easy UX. 

If dashboard filters have options associated (e.g. matching "is, contains, etc"), those should also be considered standard and included on every dashboard where that filter is included. 

A human developer may override these standards, but you don't do so unless you're told explicitly. 

#### Testing/QA
Do not run npm run sources. This is an extremely slow process and is not worth running. Let the user run manually if they choose.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:46cd31e7 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
