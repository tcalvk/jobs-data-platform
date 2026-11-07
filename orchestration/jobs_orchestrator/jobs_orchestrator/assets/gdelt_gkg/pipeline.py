"""One manually selected latest English batch, with durable restart safety."""

from datetime import datetime, timezone
import base64
import json
from pathlib import Path
import re
import tempfile

from .contract import load_contract
from .download import download_archive, fetch_latest
from .parser import ContentRejected, json_bytes, stage_parsed
from .storage import ArchiveStore, StorageConflict


def _provenance(batch):
    return {"source_url": batch.source_url, "source_expected_md5": batch.expected_md5,
            "source_expected_size_bytes": str(batch.expected_size_bytes)}


def _check_source(actual, batch):
    if actual["size_bytes"] != batch.expected_size_bytes or actual["md5"] != batch.expected_md5:
        raise StorageConflict("Stored source differs from manifest")


def ingest_one_batch(batch, contract, client, bucket="jobs_data_platform_prod", temp_dir=None):
    stamp = batch.timestamp.strftime("%Y%m%d%H%M%S")
    batch_id = stamp + ":gkg:english"
    raw_name = f"gdelt/raw/{stamp}.gkg.csv.zip"
    parsed_name = f"gdelt/parsed/contract_version={contract.version}/{stamp}.jsonl.gz"
    receipt_name = f"gdelt/receipts/contract_version={contract.version}/{stamp}.success.json"
    provenance = _provenance(batch)
    receipt_source = {**provenance, "source_expected_size_bytes": batch.expected_size_bytes}
    with tempfile.TemporaryDirectory(dir=temp_dir) as directory:
        root = Path(directory)
        store = ArchiveStore(client, bucket, root)
        receipts = [n for n in store.names("gdelt/receipts/") if n.endswith(f"/{stamp}.success.json")]
        rejects = store.names(f"gdelt/reject/{stamp}__")
        partials = [n for n in store.names("gdelt/parsed/") if n.endswith(f"/{stamp}.jsonl.gz")]
        if len(receipts) > 1 or len(rejects) > 1 or (receipts and rejects):
            raise StorageConflict("Conflicting terminal batch states")
        raw = store.get(raw_name)
        if receipts:
            blob = store.get(receipts[0])
            store.read(blob, root / "receipt")
            try:
                receipt = json.loads((root / "receipt").read_text("utf-8"))
                version = receipt["contract_version"]
                if type(version) is not int or version < 1 or receipt["batch_id"] != batch_id or receipt["batch_timestamp_utc"] != batch.timestamp.isoformat().replace("+00:00", "Z"):
                    raise ValueError()
                if receipts[0] != f"gdelt/receipts/contract_version={version}/{stamp}.success.json" or receipt["source"] != receipt_source:
                    raise ValueError()
                if any(type(receipt[k]) is not int for k in ("row_count", "accepted_row_count", "rejected_row_count")) or receipt["row_count"] < 0 or receipt["accepted_row_count"] != receipt["row_count"] or receipt["rejected_row_count"] != 0:
                    raise ValueError()
                _completion_time(receipt)
                expected_parsed = f"gdelt/parsed/contract_version={version}/{stamp}.jsonl.gz"
                if partials != [expected_parsed] or receipt["raw"]["uri"] != f"gs://{bucket}/{raw_name}" or receipt["parsed"]["uri"] != f"gs://{bucket}/{expected_parsed}":
                    raise ValueError()
                raw = store.verify_artifact(receipt["raw"])
                parsed = store.verify_artifact(receipt["parsed"])
                if raw.metadata != {**provenance, "contract_version": str(version), "sha256": receipt["raw"]["sha256"]}:
                    raise StorageConflict("Completed raw provenance conflict")
                expected_md5 = base64.b64encode(bytes.fromhex(batch.expected_md5)).decode("ascii")
                if int(raw.size) != batch.expected_size_bytes or raw.md5_hash != expected_md5:
                    raise StorageConflict("Completed raw size/MD5 conflict")
                if parsed.metadata != {"contract_version": str(version), "source_sha256": receipt["raw"]["sha256"], "sha256": receipt["parsed"]["sha256"]}:
                    raise StorageConflict("Completed parsed provenance conflict")
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                raise StorageConflict("Invalid success receipt or lineage") from exc
            return {"status": "already_complete", "batch_id": batch_id, "contract_version": version, "row_count": receipt["row_count"]}
        if rejects:
            rejected = store.get(rejects[0])
            metadata = rejected.metadata or {}
            match = re.fullmatch(rf"gdelt/reject/{stamp}__contract-v([1-9][0-9]*)__([a-z_]+)\.gkg\.csv\.zip", rejects[0])
            if not match or metadata != {**provenance, "contract_version": match[1], "reason": match[2], "sha256": metadata.get("sha256")} or partials:
                raise StorageConflict("Invalid rejected batch lineage")
            actual = store.read(rejected, root / "rejected")
            _check_source(actual, batch)
            if raw:
                if store.read(raw, root / "raw") != actual:
                    raise StorageConflict("Raw/rejected conflict")
                store.delete(raw)
            return {"status": "already_rejected", "batch_id": batch_id, "reason": match[2], "contract_version": int(match[1])}
        if any(n != parsed_name for n in partials):
            raise StorageConflict("Partial artifact belongs to another contract")
        raw_path = root / "raw.zip"
        if raw:
            if raw.metadata != {**provenance, "contract_version": str(contract.version), "sha256": (raw.metadata or {}).get("sha256")}:
                raise StorageConflict("Partial raw lineage/contract conflict")
            _check_source(store.read(raw, raw_path), batch)
        else:
            if partials:
                raise StorageConflict("Partial parsed artifact has no raw source")
            download_archive(batch, raw_path)
            raw = store.put(raw_name, raw_path, {**provenance, "contract_version": str(contract.version)})
        parsed_path = root / "parsed.gz"
        try:
            rows = stage_parsed(raw_path, parsed_path, batch, contract)
        except ContentRejected as exc:
            if partials:
                raise StorageConflict("Rejected source has an existing parsed artifact") from exc
            name = f"gdelt/reject/{stamp}__contract-v{contract.version}__{exc.reason}.gkg.csv.zip"
            # Copy the verified original bytes, then verify the destination before
            # generation-conditional deletion. No source bytes are transformed.
            store.put(name, raw_path, {**provenance, "contract_version": str(contract.version), "reason": exc.reason})
            store.delete(raw)
            return {"status": "rejected", "batch_id": batch_id, "contract_version": contract.version, "reason": exc.reason}
        parsed = store.put(parsed_name, parsed_path, {"contract_version": str(contract.version), "source_sha256": raw.metadata["sha256"]})
        receipt = {"batch_id": batch_id, "batch_timestamp_utc": batch.timestamp.isoformat().replace("+00:00", "Z"),
                   "contract_version": contract.version, "source": receipt_source, "raw": store.artifact(raw),
                   "parsed": store.artifact(parsed), "row_count": rows, "accepted_row_count": rows,
                   "rejected_row_count": 0, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        # A concurrent writer may have a different completion clock only.
        existing = store.get(receipt_name)
        if existing:
            store.read(existing, root / "receipt")
            prior = json.loads((root / "receipt").read_text("utf-8"))
            _completion_time(prior)
            comparable = lambda r: {k: v for k, v in r.items() if k != "completed_at_utc"}
            if comparable(prior) != comparable(receipt):
                raise StorageConflict("Concurrent receipt conflict")
            receipt = prior
        receipt_path = root / "success.json"
        receipt_path.write_bytes(json_bytes(receipt))
        try:
            store.put(receipt_name, receipt_path, {"contract_version": str(contract.version)})
        except StorageConflict:
            # Handle a create-only race that happened after the initial lookup.
            winner = store.get(receipt_name)
            if winner is None:
                raise
            store.read(winner, root / "receipt")
            prior = json.loads((root / "receipt").read_text("utf-8"))
            _completion_time(prior)
            if {k: v for k, v in prior.items() if k != "completed_at_utc"} != {k: v for k, v in receipt.items() if k != "completed_at_utc"}:
                raise
        return {"status": "complete", "batch_id": batch_id, "contract_version": contract.version, "row_count": rows}


def ingest_latest(storage_resource, bucket="jobs_data_platform_prod", temp_dir=None):
    contract = load_contract()  # Configuration precedes HTTP and ADC/client creation.
    batch = fetch_latest()
    return ingest_one_batch(batch, contract, storage_resource.storage_client, bucket, temp_dir)


def _completion_time(receipt):
    try:
        value = receipt["completed_at_utc"]
        if not value.endswith("Z"):
            raise ValueError()
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise StorageConflict("Invalid receipt completion time") from exc
