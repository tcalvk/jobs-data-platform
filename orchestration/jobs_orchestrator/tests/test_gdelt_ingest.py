"""Offline end-to-end tests: no ADC, HTTP, GCS or filesystem fixtures."""

from contextlib import contextmanager
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from google.api_core.exceptions import NotFound, PreconditionFailed

from jobs_orchestrator.assets.gdelt_gkg.contract import Contract, load_contract
from jobs_orchestrator.assets.gdelt_gkg.download import DownloadFailure, _retry, download_archive
from jobs_orchestrator.assets.gdelt_gkg.manifest import GkgBatchRef
from jobs_orchestrator.assets.gdelt_gkg.parser import ContentRejected
from jobs_orchestrator.assets.gdelt_gkg.pipeline import ingest_one_batch, ingest_latest
from jobs_orchestrator.assets.gdelt_gkg.storage import StorageConflict

STAMP = "20261024020000"
RAW = f"gdelt/raw/{STAMP}.gkg.csv.zip"
PARSED = f"gdelt/parsed/contract_version=1/{STAMP}.jsonl.gz"
RECEIPT = f"gdelt/receipts/contract_version=1/{STAMP}.success.json"
FIELDS = ['"literal"', "wrong source date", "你好 café"] + [""] * 24


def archive(body=None, name=None):
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(name or f"{STAMP}.gkg.csv", body if body is not None else ("\t".join(FIELDS) + "\n").encode())
    return target.getvalue()


def batch(data):
    return GkgBatchRef(f"https://data.gdeltproject.org/gdeltv2/{STAMP}.gkg.csv.zip", len(data), hashlib.md5(data).hexdigest())


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name
        self.metadata = None

    def reload(self, *, retry):
        assert retry is None
        if self.name not in self.bucket.objects:
            raise NotFound("missing")
        data, metadata, generation = self.bucket.objects[self.name]
        self.metadata, self.generation, self.size = copy.deepcopy(metadata), generation, len(data)
        self.md5_hash = base64.b64encode(hashlib.md5(data).digest()).decode("ascii")

    def upload_from_filename(self, path, *, if_generation_match, retry):
        assert retry is None and if_generation_match == 0
        if self.name in self.bucket.objects:
            raise PreconditionFailed("exists")
        self.bucket.counter += 1
        self.bucket.objects[self.name] = (Path(path).read_bytes(), copy.deepcopy(self.metadata), self.bucket.counter)
        self.bucket.events.append(("write", self.name))
        if self.bucket.crash == self.name:
            self.bucket.crash = None
            raise RuntimeError("crash after durable write")

    def download_to_filename(self, path, *, if_generation_match, retry):
        assert retry is None
        data, _, generation = self.bucket.objects[self.name]
        assert if_generation_match == generation
        self.bucket.downloads.append(self.name)
        Path(path).write_bytes(data)

    def delete(self, *, if_generation_match, retry):
        assert retry is None
        assert if_generation_match == self.bucket.objects[self.name][2]
        if self.bucket.fail_delete:
            self.bucket.fail_delete = False
            raise RuntimeError("delete failed")
        del self.bucket.objects[self.name]
        self.bucket.events.append(("delete", self.name))


class FakeStorage:
    name = "jobs_data_platform_prod"

    def __init__(self):
        self.objects, self.events = {}, []
        self.downloads = []
        self.counter = 0
        self.crash = None
        self.fail_delete = False

    def bucket(self, name):
        assert name == self.name
        return self

    def blob(self, name):
        return FakeBlob(self, name)

    def list_blobs(self, bucket, *, prefix, retry):
        assert retry is None
        return [self.blob(n) for n in sorted(self.objects) if n.startswith(prefix)]


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()
        self.data = archive()
        self.client = FakeStorage()
        self.downloads = 0

    @contextmanager
    def downloaded(self, data=None):
        data = self.data if data is None else data
        def download(ref, path):
            self.downloads += 1
            path.write_bytes(data)
        with patch("jobs_orchestrator.assets.gdelt_gkg.pipeline.download_archive", side_effect=download):
            yield batch(data)

    def run_ingest(self, data=None, contract=None):
        with self.downloaded(data) as ref:
            return ingest_one_batch(ref, contract or self.contract, self.client)

    def test_success_deterministic_original_values_receipt_last_and_skip(self):
        result = self.run_ingest()
        self.assertEqual(result["row_count"], 1)
        parsed = self.client.objects[PARSED][0]
        row = json.loads(gzip.decompress(parsed))
        self.assertEqual(list(row), ["contract_version", "batch_id", "batch_timestamp_utc", "source_columns"])
        self.assertEqual(row["batch_timestamp_utc"], "2026-10-24T02:00:00Z")
        self.assertEqual(list(row["source_columns"].values()), FIELDS)
        self.assertIn("你好".encode(), gzip.decompress(parsed))
        self.assertEqual(parsed[4:8], b"\0" * 4)
        self.assertEqual(parsed[3] & 8, 0)  # no gzip filename
        self.assertEqual(self.client.objects[RAW][0], self.data)
        self.assertEqual(self.client.events[-1], ("write", RECEIPT))
        receipt = json.loads(self.client.objects[RECEIPT][0])
        self.assertEqual(receipt["accepted_row_count"], 1)
        self.assertEqual(receipt["source"]["source_expected_md5"], batch(self.data).expected_md5)
        events = self.client.events[:]
        self.assertEqual(self.run_ingest()["status"], "already_complete")
        self.assertEqual(self.downloads, 1)
        self.assertEqual(events, self.client.events)
        other = FakeStorage()
        with self.downloaded() as ref:
            ingest_one_batch(ref, self.contract, other)
        self.assertEqual(parsed, other.objects[PARSED][0])

    def test_whole_file_rejection(self):
        valid = "\t".join(FIELDS).encode() + b"\n"
        for width in (26, 28):
            with self.subTest(width=width):
                self.client = FakeStorage()
                data = archive(valid + b"\t".join([b""] * width) + b"\n")
                self.assertEqual(self.run_ingest(data)["reason"], "field_count")
                name = next(iter(self.client.objects))
                self.assertIn("__contract-v1__field_count", name)
                self.assertEqual(self.client.objects[name][0], data)
                self.assertNotIn(RAW, self.client.objects)
                self.assertNotIn(PARSED, self.client.objects)
                self.assertNotIn(RECEIPT, self.client.objects)
                downloads = self.downloads
                self.assertEqual(self.run_ingest(data)["status"], "already_rejected")
                self.assertEqual(downloads, self.downloads)

    def test_completed_rerun_downloads_only_small_receipt(self):
        self.run_ingest()
        self.client.downloads.clear()
        with patch("jobs_orchestrator.assets.gdelt_gkg.pipeline.download_archive") as download:
            result = ingest_one_batch(batch(self.data), self.contract, self.client)
        self.assertEqual(result["status"], "already_complete")
        download.assert_not_called()
        self.assertEqual(self.client.downloads, [RECEIPT])

    def test_completed_metadata_and_generation_conflicts_fail_without_payload_reads(self):
        for name, field, value in [
            (RAW, "sha256", None), (RAW, "sha256", "invalid"),
            (RAW, "sha256", "0" * 64), (RAW, "source_url", "wrong"),
            (RAW, "source_expected_md5", None), (RAW, "source_expected_md5", "0" * 32),
            (RAW, "source_expected_size_bytes", "0"), (RAW, "contract_version", "2"),
            (PARSED, "sha256", None), (PARSED, "source_sha256", "0" * 64),
            (PARSED, "contract_version", "2"),
            (RAW, "generation", None), (PARSED, "generation", None),
            (RAW, "size", None), (PARSED, "size", None),
        ]:
            with self.subTest(name=name, field=field, value=value):
                self.client = FakeStorage()
                self.run_ingest()
                data, metadata, generation = self.client.objects[name]
                if field == "generation":
                    generation += 100
                elif field == "size":
                    data += b"changed size"
                elif value is None:
                    del metadata[field]
                else:
                    metadata[field] = value
                self.client.objects[name] = (data, metadata, generation)
                self.client.downloads.clear()
                with self.assertRaises(StorageConflict):
                    self.run_ingest()
                self.assertEqual(self.client.downloads, [RECEIPT])

    def test_completed_raw_requires_valid_gcs_md5(self):
        self.run_ingest()
        original = FakeBlob.reload
        for md5 in (None, "malformed", base64.b64encode(b"0" * 16).decode()):
            with self.subTest(md5=md5):
                def reload(blob, **kwargs):
                    original(blob, **kwargs)
                    if blob.name == RAW:
                        blob.md5_hash = md5
                self.client.downloads.clear()
                with patch.object(FakeBlob, "reload", reload), self.assertRaises(StorageConflict):
                    self.run_ingest()
                self.assertEqual(self.client.downloads, [RECEIPT])

    def test_partial_recovery_still_downloads_full_artifact_bytes(self):
        self.client.crash = PARSED
        with self.assertRaises(RuntimeError):
            self.run_ingest()
        self.client.downloads.clear()
        self.assertEqual(self.run_ingest()["status"], "complete")
        self.assertIn(RAW, self.client.downloads)
        self.assertIn(PARSED, self.client.downloads)

    def test_invalid_utf8_zip_unsafe_and_crc(self):
        corrupt = bytearray(archive())
        start = 30 + len(f"{STAMP}.gkg.csv")
        corrupt[start] ^= 1
        for data, reason in [(archive(b"\xff\t" * 26), "invalid_utf8"), (b"not zip", "invalid_zip"),
                             (archive(name="../evil"), "unsafe_zip"), (bytes(corrupt), "invalid_zip")]:
            with self.subTest(reason=reason):
                self.client = FakeStorage()
                self.assertEqual(self.run_ingest(data)["reason"], reason)
                self.assertEqual(len(self.client.objects), 1)

    def test_caps_and_encrypted_member(self):
        with patch("jobs_orchestrator.assets.gdelt_gkg.parser.MAX_ROW_BYTES", 1):
            self.assertEqual(self.run_ingest()["reason"], "row_size_cap")
        self.client = FakeStorage()
        with patch("jobs_orchestrator.assets.gdelt_gkg.parser.MAX_UNCOMPRESSED_BYTES", 1):
            self.assertEqual(self.run_ingest()["reason"], "uncompressed_size_cap")
        self.client = FakeStorage()
        with patch("jobs_orchestrator.assets.gdelt_gkg.parser.MAX_ZIP_BYTES", 1):
            self.assertEqual(self.run_ingest()["reason"], "compressed_size_cap")
        encrypted = bytearray(self.data)
        central = encrypted.index(b"PK\x01\x02")
        encrypted[central + 8] |= 1
        self.client = FakeStorage()
        self.assertEqual(self.run_ingest(bytes(encrypted))["reason"], "unsafe_zip")

    def test_empty_member_is_valid_no_undeclared_empty_rule(self):
        self.assertEqual(self.run_ingest(archive(b""))["row_count"], 0)

    def test_crash_after_each_persistence(self):
        for name in (RAW, PARSED, RECEIPT):
            with self.subTest(name=name):
                self.client = FakeStorage()
                self.client.crash = name
                self.downloads = 0
                with self.assertRaises(RuntimeError):
                    self.run_ingest()
                self.assertIn(self.run_ingest()["status"], ("complete", "already_complete"))
                self.assertEqual(self.downloads, 1)
                self.assertEqual(len(self.client.objects), 3)

    def test_reject_interrupted_copy_and_delete(self):
        data = archive(b"wrong width\n")
        rejected = f"gdelt/reject/{STAMP}__contract-v1__field_count.gkg.csv.zip"
        for crash_write in (True, False):
            with self.subTest(crash_write=crash_write):
                self.client = FakeStorage()
                self.client.crash = rejected if crash_write else None
                self.client.fail_delete = not crash_write
                with self.assertRaises(RuntimeError):
                    self.run_ingest(data)
                self.assertIn(RAW, self.client.objects)
                self.assertEqual(self.run_ingest(data)["status"], "already_rejected")
                self.assertNotIn(RAW, self.client.objects)

    def test_conflicts_never_overwrite(self):
        self.client.crash = PARSED
        with self.assertRaises(RuntimeError):
            self.run_ingest()
        content, metadata, generation = self.client.objects[PARSED]
        self.client.objects[PARSED] = (b"corrupt", metadata, generation)
        before = copy.deepcopy(self.client.objects)
        with self.assertRaises(StorageConflict):
            self.run_ingest()
        self.assertEqual(before, self.client.objects)

    def test_partial_raw_other_contract_conflict(self):
        self.client.crash = RAW
        with self.assertRaises(RuntimeError):
            self.run_ingest()
        with self.assertRaises(StorageConflict):
            self.run_ingest(contract=Contract(2, self.contract.columns))

    def test_completed_and_rejected_old_contract_skip(self):
        self.run_ingest()
        self.assertEqual(self.run_ingest(contract=Contract(2, self.contract.columns))["status"], "already_complete")
        self.client = FakeStorage()
        data = archive(b"bad\n")
        self.run_ingest(data)
        self.assertEqual(self.run_ingest(data, Contract(2, self.contract.columns))["status"], "already_rejected")

    def test_corrupt_receipt_or_missing_artifact_fail(self):
        self.run_ingest()
        del self.client.objects[PARSED]
        with self.assertRaises(StorageConflict):
            self.run_ingest()
        self.client = FakeStorage()
        self.run_ingest()
        data, metadata, gen = self.client.objects[RECEIPT]
        self.client.objects[RECEIPT] = (b"{}", metadata, gen)
        with self.assertRaises(StorageConflict):
            self.run_ingest()

    def test_contract_bad_fails_before_client_or_http(self):
        with patch("jobs_orchestrator.assets.gdelt_gkg.pipeline.load_contract", side_effect=ValueError), patch("jobs_orchestrator.assets.gdelt_gkg.pipeline.fetch_latest") as fetch:
            with self.assertRaises(ValueError):
                ingest_latest(object())
            fetch.assert_not_called()

    def test_gcs_failure_no_retry_or_source_rejection(self):
        with patch.object(self.client, "list_blobs", side_effect=PermissionError) as listing:
            with self.assertRaises(PermissionError):
                self.run_ingest()
            self.assertEqual(listing.call_count, 1)
        self.assertEqual(self.client.objects, {})

    def test_create_only_races_converge_including_receipt_clock(self):
        original = FakeBlob.upload_from_filename
        raced = set()
        def concurrent_upload(blob, path, **kwargs):
            if blob.name not in raced:
                raced.add(blob.name)
                if blob.name == RECEIPT:
                    value = json.loads(Path(path).read_bytes())
                    value["completed_at_utc"] = "2026-10-24T02:00:01Z"
                    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                    metadata = {**blob.metadata, "sha256": hashlib.sha256(payload).hexdigest()}
                else:
                    payload, metadata = Path(path).read_bytes(), blob.metadata
                self.client.counter += 1
                self.client.objects[blob.name] = (payload, metadata, self.client.counter)
            return original(blob, path, **kwargs)
        with patch.object(FakeBlob, "upload_from_filename", concurrent_upload):
            self.assertEqual(self.run_ingest()["status"], "complete")
        self.assertEqual(self.run_ingest()["status"], "already_complete")
        self.assertEqual(json.loads(self.client.objects[RECEIPT][0])["completed_at_utc"], "2026-10-24T02:00:01Z")

    def test_partial_parsed_is_revalidated_not_assumed_complete(self):
        self.client.crash = PARSED
        with self.assertRaises(RuntimeError):
            self.run_ingest()
        with patch("jobs_orchestrator.assets.gdelt_gkg.pipeline.stage_parsed", side_effect=ContentRejected("field_count")) as parse:
            with self.assertRaises(StorageConflict):
                self.run_ingest()
            parse.assert_called_once()
        self.assertNotIn(RECEIPT, self.client.objects)

    def test_partial_parsed_other_contract_fails_without_mutation(self):
        self.client.crash = PARSED
        with self.assertRaises(RuntimeError):
            self.run_ingest()
        before = copy.deepcopy(self.client.objects)
        with self.assertRaises(StorageConflict):
            self.run_ingest(contract=Contract(2, self.contract.columns))
        self.assertEqual(before, self.client.objects)

    def test_reject_raw_conflict_does_not_delete(self):
        data = archive(b"bad\n")
        self.client.fail_delete = True
        with self.assertRaises(RuntimeError):
            self.run_ingest(data)
        _, metadata, generation = self.client.objects[RAW]
        self.client.objects[RAW] = (b"changed", metadata, generation)
        with self.assertRaises(StorageConflict):
            self.run_ingest(data)
        self.assertIn(RAW, self.client.objects)


class ConfigurationAndDownloadTests(unittest.TestCase):
    def test_bad_contracts(self):
        original = Path(__import__("jobs_orchestrator.assets.gdelt_gkg.contract", fromlist=["x"]).__file__).with_name("contracts.yml").read_text()
        for text in [original.replace("active_contract_version: 1", "active_contract_version: 9"),
                     original.replace("+type: string", "+type: integer", 1),
                     original.replace("rules: []", "rules: [required_id]"),
                     original.replace("quoting: literal", "quoting: csv"), "{malformed"]:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "contract.yml"
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_contract(path)

    def test_duplicate_yaml_keys_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.yml"
            path.write_text("active_contract_version: 1\nactive_contract_version: 2\ncontracts: {}\n")
            with self.assertRaises(ValueError):
                load_contract(path)

    def test_ingest_job_only_initializes_storage_not_bq(self):
        from dagster import AssetKey
        from jobs_orchestrator.definitions import defs
        from jobs_orchestrator.resources.gdelt_storage import GdeltStorageResource
        job = defs.resolve_job_def("gdelt_gkg_ingest_job")
        self.assertEqual(job.asset_layer.executable_asset_keys, {AssetKey("gdelt_gkg_ingest")})
        with patch("jobs_orchestrator.assets.gdelt_gkg.ingest_asset.ingest_latest", return_value={"status": "complete", "row_count": 0}), patch.dict("os.environ", {}, clear=True), patch.object(GdeltStorageResource, "storage_client", new_callable=unittest.mock.PropertyMock) as client:
            result = job.execute_in_process()
            self.assertTrue(result.success)
            client.assert_not_called()

    def test_retries_three_total_and_permanent_http(self):
        from urllib.error import HTTPError
        for error in (TimeoutError(), DownloadFailure(), HTTPError("url", 429, "", {}, None), HTTPError("url", 503, "", {}, None)):
            calls = []
            def operation():
                calls.append(1)
                raise error
            with self.assertRaises(DownloadFailure):
                _retry(operation, sleep=lambda _: None)
            self.assertEqual(len(calls), 3)
        operation = unittest.mock.Mock(side_effect=HTTPError("url", 404, "", {}, None))
        with self.assertRaises(DownloadFailure):
            _retry(operation, sleep=lambda _: None)
        self.assertEqual(operation.call_count, 1)
        operation = unittest.mock.Mock(side_effect=[TimeoutError(), "ok"])
        self.assertEqual(_retry(operation, sleep=lambda _: None), "ok")

    def test_download_verification_retry(self):
        data = archive()
        streams = [io.BytesIO(b"bad"), io.BytesIO(data)]
        with tempfile.TemporaryDirectory() as temp, patch("jobs_orchestrator.assets.gdelt_gkg.sample._open", side_effect=streams) as opened, patch("jobs_orchestrator.assets.gdelt_gkg.download._retry", side_effect=lambda op: _retry(op, sleep=lambda _: None)):
            path = Path(temp) / "raw"
            download_archive(batch(data), path)
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(opened.call_count, 2)


if __name__ == "__main__":
    unittest.main()
