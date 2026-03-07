from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from google.cloud import bigquery
from google.cloud import storage

if os.getenv("ENV", "local") == "local":
    from dotenv import load_dotenv

    load_dotenv()


DEFAULT_GCS_PREFIX = "serpapi"
DEFAULT_BATCH_SIZE = 500


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_table_id(env_value: str, project_id: str, label: str) -> str:
    table_id = env_value.strip()
    if not table_id:
        raise ValueError(f"Missing {label} env var.")
    if table_id.count(".") >= 2:
        return table_id
    if not project_id:
        raise ValueError(f"Missing BQ_PROJECT_ID for {label} table resolution.")
    return f"{project_id}.{table_id}"


def _fetch_loaded_objects(
    bq_client: bigquery.Client,
    ledger_table_id: str,
    bucket: str,
    target_table_id: str,
) -> Set[str]:
    query = (
        "SELECT object_name FROM `" + ledger_table_id + "` "
        "WHERE bucket = @bucket AND target_table_id = @target_table_id"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("bucket", "STRING", bucket),
            bigquery.ScalarQueryParameter(
                "target_table_id", "STRING", target_table_id
            ),
        ]
    )
    rows = bq_client.query(query, job_config=job_config).result()
    return {row["object_name"] for row in rows}


def _list_jsonl_blobs(
    storage_client: storage.Client, bucket_name: str, prefix: str
) -> List[storage.Blob]:
    blob_iter = storage_client.list_blobs(bucket_name, prefix=prefix)
    return [blob for blob in blob_iter if blob.name.endswith(".jsonl")]


def _iter_jsonl_records(blob: storage.Blob) -> Iterable[Dict[str, Any]]:
    with blob.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                yield json.loads(text)
            except json.JSONDecodeError as exc:
                print(f"Skipping invalid JSON line in {blob.name}: {exc}")


def _build_bq_row(record: Dict[str, Any], gcs_uri: str) -> Dict[str, Any]:
    return {
        "created_at": record.get("fetched_at"),
        "job_data": record,
        "query_version_id": record.get("query_id"),
        "gcs_uri": gcs_uri,
    }


def _load_batch(
    bq_client: bigquery.Client, table_id: str, rows: List[Dict[str, Any]]
) -> None:
    if not rows:
        return
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    job = bq_client.load_table_from_json(rows, table_id, job_config=job_config)
    job.result()


def _load_object(
    bq_client: bigquery.Client,
    blob: storage.Blob,
    table_id: str,
    batch_size: int,
) -> int:
    gcs_uri = f"gs://{blob.bucket.name}/{blob.name}"
    rows: List[Dict[str, Any]] = []
    loaded = 0
    for record in _iter_jsonl_records(blob):
        rows.append(_build_bq_row(record, gcs_uri))
        if len(rows) >= batch_size:
            _load_batch(bq_client, table_id, rows)
            loaded += len(rows)
            rows = []
    if rows:
        _load_batch(bq_client, table_id, rows)
        loaded += len(rows)
    return loaded


def _insert_load_ledger(
    bq_client: bigquery.Client,
    ledger_table_id: str,
    object_name: str,
    bucket: str,
    target_table_id: str,
) -> None:
    row = {
        "object_name": object_name,
        "bucket": bucket,
        "target_table_id": target_table_id,
        "loaded_at": _now_utc().isoformat(),
    }
    errors = bq_client.insert_rows_json(ledger_table_id, [row])
    if errors:
        raise RuntimeError(f"Failed to insert load ledger row: {errors}")


def main() -> None:
    bucket_name = os.environ.get("GCS_BUCKET", "").strip()
    if not bucket_name:
        raise ValueError("Missing GCS_BUCKET env var.")

    project_id = os.environ.get("BQ_PROJECT_ID", "").strip()
    raw_table_env = os.environ.get("BQ_RAW_TABLE_ID", "")
    ledger_table_env = os.environ.get("BQ_LOAD_LEDGER_ID", "")
    raw_table_id = _resolve_table_id(raw_table_env, project_id, "BQ_RAW_TABLE_ID")
    ledger_table_id = _resolve_table_id(
        ledger_table_env, project_id, "BQ_LOAD_LEDGER_ID"
    )

    prefix_env = os.environ.get("GCS_PREFIX", "").strip().strip("/")
    prefix = prefix_env or DEFAULT_GCS_PREFIX
    if prefix:
        prefix = prefix + "/"

    batch_size = int(os.environ.get("LOAD_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))

    bq_client = bigquery.Client()
    storage_client = storage.Client()

    loaded_objects = _fetch_loaded_objects(
        bq_client, ledger_table_id, bucket_name, raw_table_id
    )
    blobs = _list_jsonl_blobs(storage_client, bucket_name, prefix)
    if not blobs:
        print("No JSONL objects found to load.")
        return

    for blob in blobs:
        if blob.name in loaded_objects:
            continue

        gcs_uri = f"gs://{bucket_name}/{blob.name}"
        try:
            loaded_count = _load_object(bq_client, blob, raw_table_id, batch_size)
        except Exception as exc:
            print(f"Failed to load {gcs_uri}: {exc}")
            continue

        try:
            _insert_load_ledger(
                bq_client, ledger_table_id, blob.name, bucket_name, raw_table_id
            )
        except Exception as exc:
            print(f"Loaded {gcs_uri} but failed to update ledger: {exc}")
            continue

        print(f"Loaded {loaded_count} rows from {gcs_uri}")


if __name__ == "__main__":
    main()
