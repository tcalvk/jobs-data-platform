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
  - `serpapi_get_jobs`: `GCS_BUCKET` plus `BQ_TABLE_ID` or `BQ_PROJECT_ID`/`GOOGLE_CLOUD_PROJECT`/`GCP_PROJECT`.
  - `gcs_to_bq_load`: `GCS_BUCKET`, `BQ_RAW_TABLE_ID`, `BQ_LOAD_LEDGER_ID`; `BQ_PROJECT_ID` is needed unless table IDs are fully qualified.
  - `enrich_skills`: `BQ_JOBS_DIM_TABLE_ID`, `GROQ_API_KEY_ICLOUD`, `GROQ_API_KEY_GOOGLE`, plus `BQ_PROJECT_ID`/`GOOGLE_CLOUD_PROJECT`/`GCP_PROJECT`.
- `serpapi_get_jobs` reads SerpApi keys from `projects-portfolio-446806.seeds.serpapi_accounts`, not from a local `SERPAPI_API_KEY` env var.

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