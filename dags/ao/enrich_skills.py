from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from google.cloud import bigquery
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

if os.getenv("ENV", "local") == "local":
    from dotenv import load_dotenv

    load_dotenv()


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL_ID = os.environ.get("GROQ_MODEL_ID", "llama-3.1-8b-instant")
REQUESTS_PER_MINUTE = 30


@dataclass
class GroqClientState:
    label: str
    client: OpenAI
    window_start: float
    request_count: int = 0
    cooldown_until: float = 0.0
    success_count: int = 0
    rate_limited_count: int = 0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing {name} env var.")
    return value


def _resolve_project_id() -> str:
    project_id = (
        os.environ.get("BQ_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or ""
    ).strip()
    if not project_id:
        raise ValueError("Missing BQ_PROJECT_ID or GOOGLE_CLOUD_PROJECT/GCP_PROJECT.")
    return project_id


def _get_jobs_to_enrich(
    bq_client: bigquery.Client,
    project_id: str,
    jobs_dim_table_id: str,
    daily_max_jobs: int,
) -> List[Dict[str, str]]:
    query = f"""
        SELECT src.job_id, src.data_source, src.job_description
        FROM `{project_id}.{jobs_dim_table_id}` AS src
        WHERE src.job_description IS NOT NULL
          AND TRIM(src.job_description) != ''
          AND src.data_source IS NOT NULL
          AND TRIM(src.data_source) != ''
          AND NOT EXISTS (
            SELECT 1
            FROM `{project_id}.ao.enrich_skills` AS tgt
            WHERE tgt.job_id = src.job_id
              AND tgt.data_source = src.data_source
          )
        ORDER BY src.created_at_utc ASC
        LIMIT @daily_max_jobs
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("daily_max_jobs", "INT64", daily_max_jobs)
        ]
    )
    rows = bq_client.query(query, job_config=job_config).result()
    return [
        {
            "job_id": str(row["job_id"]),
            "data_source": str(row["data_source"]),
            "job_description": str(row["job_description"]),
        }
        for row in rows
    ]


def _log_rate_limit_headers(headers: Dict[str, str], prefix: str) -> None:
    keys = [
        "retry-after",
        "x-ratelimit-limit-requests",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset-tokens",
    ]
    available = {k: headers.get(k) for k in keys if headers.get(k) is not None}
    if available:
        print(f"{prefix} rate-limit headers: {available}")


def _parse_retry_after(headers: Dict[str, str]) -> Optional[float]:
    value = headers.get("retry-after")
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


def _pace_rpm(client_state: GroqClientState) -> None:
    if client_state.request_count < REQUESTS_PER_MINUTE:
        return

    elapsed = time.monotonic() - client_state.window_start
    if elapsed < 60:
        sleep_for = 60 - elapsed
        print(
            f"[{client_state.label}] Reached {REQUESTS_PER_MINUTE} requests; "
            f"sleeping {sleep_for:.2f}s"
        )
        time.sleep(sleep_for)

    client_state.window_start = time.monotonic()
    client_state.request_count = 0


def _get_next_available_client(
    clients: List[GroqClientState],
    next_index: int,
) -> Tuple[GroqClientState, int]:
    now = time.monotonic()
    count = len(clients)

    for offset in range(count):
        idx = (next_index + offset) % count
        if clients[idx].cooldown_until <= now:
            return clients[idx], (idx + 1) % count

    sleep_for = min(max(client.cooldown_until - now, 0.0) for client in clients)
    if sleep_for > 0:
        print(f"All Groq keys cooling down; sleeping {sleep_for:.2f}s")
        time.sleep(sleep_for)

    now = time.monotonic()
    for offset in range(count):
        idx = (next_index + offset) % count
        if clients[idx].cooldown_until <= now:
            return clients[idx], (idx + 1) % count

    return clients[next_index % count], (next_index + 1) % count


def _extract_headers_from_error(exc: Exception) -> Dict[str, str]:
    if isinstance(exc, APIStatusError) and getattr(exc, "response", None) is not None:
        headers = getattr(exc.response, "headers", {})
        return {k.lower(): v for k, v in headers.items()}
    return {}


def _extract_skills_once(
    groq_client: OpenAI,
    client_label: str,
    job_description: str,
    timeout_seconds: int,
    max_output_tokens: int,
) -> str:
    system_prompt = (
        "You extract skills from job descriptions. "
        "Return only a comma-separated list of skills. "
        "No intro text, explanation, bullets, or numbering."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Extract skills from this job description:\n\n{job_description}",
        },
    ]

    try:
        raw_response = groq_client.chat.completions.with_raw_response.create(
            model=MODEL_ID,
            messages=messages,
            temperature=0.2,
            max_tokens=max_output_tokens,
            timeout=timeout_seconds,
        )
        headers = {k.lower(): v for k, v in raw_response.headers.items()}
        _log_rate_limit_headers(headers, f"Groq response [{client_label}]")
        completion = raw_response.parse()
    except AttributeError:
        completion = groq_client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            temperature=0.2,
            max_tokens=max_output_tokens,
            timeout=timeout_seconds,
        )

    text = completion.choices[0].message.content or ""
    return text.strip()


def _extract_skills_with_retries(
    clients: List[GroqClientState],
    next_index: int,
    job_id: str,
    data_source: str,
    job_description: str,
    max_retries: int,
    cooldown_seconds: int,
    timeout_seconds: int,
    max_output_tokens: int,
) -> Tuple[str, int]:
    for attempt in range(max_retries + 1):
        client_state, next_index = _get_next_available_client(clients, next_index)
        _pace_rpm(client_state)
        client_state.request_count += 1

        try:
            skills = _extract_skills_once(
                client_state.client,
                client_state.label,
                job_description,
                timeout_seconds,
                max_output_tokens,
            )
            client_state.success_count += 1
            return skills, next_index
        except RateLimitError as exc:
            headers = _extract_headers_from_error(exc)
            _log_rate_limit_headers(headers, f"Groq 429 [{client_state.label}]")

            retry_after = _parse_retry_after(headers)
            sleep_for = retry_after if retry_after is not None else float(cooldown_seconds)
            client_state.cooldown_until = max(
                client_state.cooldown_until,
                time.monotonic() + sleep_for,
            )
            client_state.rate_limited_count += 1

            if attempt >= max_retries:
                raise

            print(
                f"[{client_state.label}] Rate limited for ({job_id}, {data_source}) "
                f"on attempt {attempt + 1}; cooling key for {sleep_for:.2f}s"
            )
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            headers = _extract_headers_from_error(exc)
            _log_rate_limit_headers(headers, f"Groq API error [{client_state.label}]")

            is_rate_limit = status_code == 429
            is_retryable_server = status_code is not None and 500 <= int(status_code) < 600

            if not is_rate_limit and not is_retryable_server:
                raise
            if attempt >= max_retries:
                raise

            if is_rate_limit:
                retry_after = _parse_retry_after(headers)
                sleep_for = (
                    retry_after if retry_after is not None else float(cooldown_seconds)
                )
                client_state.cooldown_until = max(
                    client_state.cooldown_until,
                    time.monotonic() + sleep_for,
                )
                client_state.rate_limited_count += 1
            else:
                base = 5 * (2**attempt)
                sleep_for = min(60.0, float(base + random.uniform(0, 1)))
                time.sleep(sleep_for)

            print(
                f"[{client_state.label}] Retryable API error (status={status_code}) for "
                f"({job_id}, {data_source}) on attempt {attempt + 1}; "
                f"delay={sleep_for:.2f}s"
            )
        except (APIConnectionError, APITimeoutError) as exc:
            if attempt >= max_retries:
                raise

            base = 5 * (2**attempt)
            sleep_for = min(60.0, float(base + random.uniform(0, 1)))
            print(
                f"[{client_state.label}] Transient connection/timeout error for "
                f"({job_id}, {data_source}) "
                f"on attempt {attempt + 1}: {exc}. Sleeping {sleep_for:.2f}s"
            )
            time.sleep(sleep_for)

    raise RuntimeError("Unreachable retry loop state in _extract_skills_with_retries")


def _build_groq_clients() -> List[GroqClientState]:
    api_key_icloud = _require_env("GROQ_API_KEY_ICLOUD")
    api_key_google = _require_env("GROQ_API_KEY_GOOGLE")

    now = time.monotonic()
    return [
        GroqClientState(
            label="icloud",
            client=OpenAI(base_url=GROQ_BASE_URL, api_key=api_key_icloud),
            window_start=now,
        ),
        GroqClientState(
            label="google",
            client=OpenAI(base_url=GROQ_BASE_URL, api_key=api_key_google),
            window_start=now,
        ),
    ]


def _upload_skills(
    bq_client: bigquery.Client,
    rows: List[Dict[str, Any]],
    table_id: str,
) -> None:
    if not rows:
        return

    frame = pd.DataFrame(rows)
    frame["job_id"] = frame["job_id"].astype(str)
    frame["data_source"] = frame["data_source"].astype(str)
    frame["skills"] = frame["skills"].astype(str)
    frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True, errors="coerce")

    if frame["created_at"].isna().any():
        frame.loc[frame["created_at"].isna(), "created_at"] = pd.Timestamp.now(tz="UTC")

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("job_id", "STRING"),
            bigquery.SchemaField("data_source", "STRING"),
            bigquery.SchemaField("skills", "STRING"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
        ],
    )
    job = bq_client.load_table_from_dataframe(frame, table_id, job_config=job_config)
    job.result()


def main() -> int:
    project_id = _resolve_project_id()
    jobs_dim_table_id = _require_env("BQ_JOBS_DIM_TABLE_ID")

    daily_max_jobs = int(os.environ.get("ENRICH_SKILLS_DAILY_MAX_JOBS", "300"))
    cooldown_seconds = int(os.environ.get("GROQ_COOLDOWN_SECONDS", "60"))
    max_retries = int(os.environ.get("GROQ_MAX_RETRIES", "2"))
    timeout_seconds = int(os.environ.get("GROQ_REQUEST_TIMEOUT_SECONDS", "45"))
    max_output_tokens = int(os.environ.get("GROQ_MAX_OUTPUT_TOKENS", "200"))
    upload_batch_size = int(os.environ.get("ENRICH_SKILLS_UPLOAD_BATCH_SIZE", "50"))
    if upload_batch_size <= 0:
        raise ValueError("ENRICH_SKILLS_UPLOAD_BATCH_SIZE must be greater than 0.")

    key_strategy = os.environ.get("GROQ_KEY_STRATEGY", "round_robin").strip().lower()
    if key_strategy != "round_robin":
        raise ValueError("Unsupported GROQ_KEY_STRATEGY. Supported value: 'round_robin'.")

    target_table_id = f"{project_id}.ao.enrich_skills"

    bq_client = bigquery.Client(project=project_id)
    groq_clients = _build_groq_clients()

    jobs = _get_jobs_to_enrich(
        bq_client=bq_client,
        project_id=project_id,
        jobs_dim_table_id=jobs_dim_table_id,
        daily_max_jobs=daily_max_jobs,
    )

    if not jobs:
        print("No jobs need skill enrichment.")
        return 0

    print(f"Found {len(jobs)} jobs to enrich (daily max: {daily_max_jobs}).")

    enriched_rows: List[Dict[str, Any]] = []
    failed: List[Dict[str, str]] = []
    total_uploaded = 0
    next_key_index = 0

    for idx, row in enumerate(jobs, start=1):
        job_id = row["job_id"]
        data_source = row["data_source"]
        job_description = row["job_description"]

        try:
            skills, next_key_index = _extract_skills_with_retries(
                clients=groq_clients,
                next_index=next_key_index,
                job_id=job_id,
                data_source=data_source,
                job_description=job_description,
                max_retries=max_retries,
                cooldown_seconds=cooldown_seconds,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
            )
            enriched_rows.append(
                {
                    "job_id": job_id,
                    "data_source": data_source,
                    "skills": skills,
                    "created_at": _now_utc(),
                }
            )
        except Exception as exc:
            failed.append({"job_id": job_id, "data_source": data_source})
            print(f"Failed to enrich ({job_id}, {data_source}): {exc}")
        else:
            if len(enriched_rows) >= upload_batch_size:
                batch_count = len(enriched_rows)
                _upload_skills(bq_client, enriched_rows, target_table_id)
                total_uploaded += batch_count
                print(f"Uploaded batch of {batch_count} rows to {target_table_id}")
                enriched_rows.clear()

        if idx % 25 == 0 or idx == len(jobs):
            print(
                f"Progress: {idx}/{len(jobs)} processed; "
                f"success={total_uploaded + len(enriched_rows)} failed={len(failed)}"
            )

    final_batch_count = len(enriched_rows)
    _upload_skills(bq_client, enriched_rows, target_table_id)
    total_uploaded += final_batch_count
    print(f"Uploaded {total_uploaded} total rows to {target_table_id}")

    key_stats = [
        {
            "key": client.label,
            "success": client.success_count,
            "rate_limited": client.rate_limited_count,
        }
        for client in groq_clients
    ]
    print(f"Groq key stats: {key_stats}")

    if failed:
        print(f"Failed rows for replay: {failed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
