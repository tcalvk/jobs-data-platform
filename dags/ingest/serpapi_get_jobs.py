##############################################################################
# imports and global vars # 

from __future__ import annotations

import itertools
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import unquote_plus, urlencode
from urllib.request import Request, urlopen

from google.cloud import bigquery
from google.cloud import storage
if os.getenv("ENV", "local") == "local":
    from dotenv import load_dotenv
    load_dotenv()

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_MAX_JOBS = 250
DEFAULT_SOURCE_NAME = "serpapi"
SERPAPI_ACCOUNTS_TABLE = "projects-portfolio-446806.jobs_scraping.serpapi_accounts"

##############################################################################
# functions #

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_api_keys_from_bq(bq_client: bigquery.Client) -> List[str]:
    query = f"SELECT key_string FROM `{SERPAPI_ACCOUNTS_TABLE}`"
    rows = bq_client.query(query).result()
    keys = [row["key_string"].strip() for row in rows if row["key_string"] and row["key_string"].strip()]
    if not keys:
        raise ValueError(f"No API keys found in {SERPAPI_ACCOUNTS_TABLE}.")
    return keys


def _resolve_table_id() -> str:
    table_id = os.environ.get("BQ_TABLE_ID", "").strip()
    if table_id:
        return table_id
    project_id = (
        os.environ.get("BQ_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or ""
    ).strip()
    if not project_id:
        raise ValueError("Missing BQ_TABLE_ID or BQ_PROJECT_ID/GOOGLE_CLOUD_PROJECT.")
    return f"{project_id}.seeds.serpapi_query_versions"


def _fetch_query_versions(bq_client: bigquery.Client, table_id: str) -> List[Dict[str, Any]]:
    query = f"""
        SELECT
            query_id,
            q,
            location,
            hl,
            gl,
            max_jobs,
            google_domain,
            active
        FROM `{table_id}`
        WHERE active = 1
    """
    rows = bq_client.query(query).result()
    return [dict(row) for row in rows]


def _serpapi_request(params: Dict[str, Any], api_key: str, timeout_s: int = 30) -> Dict[str, Any]:
    query_params = dict(params)
    query_params["api_key"] = api_key
    url = f"{SERPAPI_ENDPOINT}?{urlencode(query_params)}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_json_endpoint(json_endpoint: str, timeout_s: int = 30) -> Dict[str, Any]:
    req = Request(json_endpoint, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _serpapi_fetch_with_retry(
    params: Dict[str, Any],
    api_keys: List[str],
    exhausted_keys: set,
    max_retries: int = 3,
    backoff_s: float = 2.0,
) -> Dict[str, Any]:
    available = [k for k in api_keys if k not in exhausted_keys]
    if not available:
        raise RuntimeError("All SerpApi keys have been exhausted.")
    key_cycle = itertools.cycle(available)
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        api_key = next(key_cycle)
        try:
            return _serpapi_request(params, api_key)
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                print(f"SerpApi key ending ...{api_key[-6:]} is exhausted (429); skipping for remainder of run.")
                exhausted_keys.add(api_key)
                available = [k for k in api_keys if k not in exhausted_keys]
                if not available:
                    raise RuntimeError("All SerpApi keys have been exhausted.") from exc
                key_cycle = itertools.cycle(available)
                continue
            if exc.code in {500, 502, 503, 504} and attempt < max_retries:
                time.sleep(backoff_s * attempt)
                continue
            raise
        except URLError as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(backoff_s * attempt)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("SerpApi request failed without an explicit error.")


def _normalize_query_row(row: Dict[str, Any]) -> Dict[str, Any]:
    max_jobs = row.get("max_jobs")
    if max_jobs is None or max_jobs == 0:
        max_jobs = int(os.environ.get("DEFAULT_MAX_JOBS", str(DEFAULT_MAX_JOBS)))
    def _clean(value: Any, decode: bool = False) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if decode:
            text = unquote_plus(text)
        return text or None
    return {
        "query_id": row.get("query_id"),
        "q": _clean(row.get("q"), decode=True),
        "location": _clean(row.get("location"), decode=True),
        "hl": _clean(row.get("hl")),
        "gl": _clean(row.get("gl")),
        "google_domain": _clean(row.get("google_domain")),
        "max_jobs": int(max_jobs),
    }


def _build_params(row: Dict[str, Any], next_page_token: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "engine": "google_jobs",
        "q": row["q"],
    }
    for key in ("location", "hl", "gl", "google_domain"):
        if row.get(key):
            params[key] = row[key]
    if next_page_token:
        params["next_page_token"] = next_page_token
    return params


def _iter_jobs_for_query(
    row: Dict[str, Any],
    api_keys: List[str],
    exhausted_keys: set,
    source_name: str,
    debug_query_id: Optional[int],
) -> List[Dict[str, Any]]:
    query_id = row["query_id"]
    max_jobs = row["max_jobs"]
    next_page_token: Optional[str] = None
    collected: List[Dict[str, Any]] = []
    page = 0
    delay_s = float(os.environ.get("REQUEST_DELAY_SECONDS", "0"))
    poll_attempts = int(os.environ.get("PROCESSING_POLL_ATTEMPTS", "6"))
    poll_delay_s = float(os.environ.get("PROCESSING_POLL_DELAY_SECONDS", "2"))

    while True:
        if max_jobs and len(collected) >= max_jobs:
            break

        params = _build_params(row, next_page_token)
        response = _serpapi_fetch_with_retry(params, api_keys, exhausted_keys)
        metadata = response.get("search_metadata", {}) or {}
        status = metadata.get("status")
        if status == "Error":
            print(f"[query_id={query_id}] SerpApi error: {metadata.get('error')}")
            break
        if status == "Processing":
            json_endpoint = metadata.get("json_endpoint")
            if json_endpoint:
                for _ in range(poll_attempts):
                    time.sleep(poll_delay_s)
                    response = _fetch_json_endpoint(json_endpoint)
                    metadata = response.get("search_metadata", {}) or {}
                    status = metadata.get("status")
                    if status != "Processing":
                        break
            if status == "Error":
                print(f"[query_id={query_id}] SerpApi error: {metadata.get('error')}")
                break

        jobs = response.get("jobs_results") or []
        if not jobs:
            if debug_query_id is not None and query_id == debug_query_id:
                debug_payload = {
                    "query_id": query_id,
                    "params": params,
                    "status": status,
                    "search_metadata": response.get("search_metadata"),
                    "search_parameters": response.get("search_parameters"),
                    "serpapi_pagination": response.get("serpapi_pagination"),
                    "jobs_results_len": len(jobs),
                    "top_keys": list(response.keys()),
                }
                print(f"DEBUG empty jobs: {json.dumps(debug_payload, ensure_ascii=True)}")
            if status == "Processing":
                print(f"[query_id={query_id}] SerpApi still processing; no jobs returned.")
            break

        page += 1
        for job in jobs:
            if max_jobs and len(collected) >= max_jobs:
                break
            collected.append(
                {
                    "source_name": source_name,
                    "query_id": query_id,
                    "q": row.get("q"),
                    "location": row.get("location"),
                    "hl": row.get("hl"),
                    "gl": row.get("gl"),
                    "google_domain": row.get("google_domain"),
                    "fetched_at": _now_utc_iso(),
                    "page": page,
                    "serpapi_search_id": metadata.get("id"),
                    "serpapi_json_endpoint": metadata.get("json_endpoint"),
                    "job": job,
                }
            )

        next_page_token = (
            response.get("serpapi_pagination", {}) or {}
        ).get("next_page_token")
        if not next_page_token:
            break

        if delay_s:
            time.sleep(delay_s)

    return collected


def _upload_jsonl(
    storage_client: storage.Client,
    bucket_name: str,
    object_name: str,
    records: List[Dict[str, Any]],
) -> None:
    if not records:
        print(f"No records to upload for {object_name}.")
        return

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        for record in records:
            tmp.write(json.dumps(record, ensure_ascii=True) + "\n")
        tmp_path = tmp.name

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(tmp_path, content_type="application/jsonl")

    os.unlink(tmp_path)


def main() -> None:
    bucket_name = os.environ.get("GCS_BUCKET", "").strip()
    if not bucket_name:
        raise ValueError("Missing GCS_BUCKET env var.")

    source_name = os.environ.get("SOURCE_NAME", DEFAULT_SOURCE_NAME).strip()
    gcs_prefix = os.environ.get("GCS_PREFIX", "").strip().strip("/")
    if gcs_prefix == bucket_name:
        gcs_prefix = ""
    debug_query_id_env = os.environ.get("DEBUG_QUERY_ID", "").strip()
    debug_query_id = int(debug_query_id_env) if debug_query_id_env.isdigit() else None
    table_id = _resolve_table_id()

    bq_client = bigquery.Client()
    api_keys = _load_api_keys_from_bq(bq_client)
    exhausted_keys: set = set()
    storage_client = storage.Client()

    query_rows = _fetch_query_versions(bq_client, table_id)
    if not query_rows:
        print("No active query versions found.")
        return

    for raw_row in query_rows:
        row = _normalize_query_row(raw_row)
        if not row.get("q"):
            print(f"Skipping query_id={row.get('query_id')} due to missing q.")
            continue

        records = _iter_jobs_for_query(row, api_keys, exhausted_keys, source_name, debug_query_id)
        timestamp = _timestamp_slug()
        if gcs_prefix:
            object_name = (
                f"{gcs_prefix}/{source_name}/{row['query_id']}/{timestamp}.jsonl"
            )
        else:
            object_name = f"{source_name}/{row['query_id']}/{timestamp}.jsonl"
        _upload_jsonl(storage_client, bucket_name, object_name, records)
        print(f"Uploaded {len(records)} records to gs://{bucket_name}/{object_name}")


if __name__ == "__main__":
    main()
