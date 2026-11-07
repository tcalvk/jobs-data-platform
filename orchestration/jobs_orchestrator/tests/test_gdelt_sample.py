import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from jobs_orchestrator.assets.gdelt_gkg.manifest import GkgBatchRef, parse_latest_manifest
from jobs_orchestrator.assets.gdelt_gkg import sample

URL = "https://data.gdeltproject.org/gdeltv2/20261024020000.gkg.csv.zip"
NAME = "20261024020000.gkg.csv"


def batch(data):
    return GkgBatchRef(URL, len(data), hashlib.md5(data).hexdigest())


def zip_bytes(text, name=NAME):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


class GdeltSampleTests(unittest.TestCase):
    def test_latest_selects_gkg_not_position(self):
        row = f"123 {'a' * 32} {URL.replace('https:', 'http:')}"
        result = parse_latest_manifest(row + "\n456 abc http://data.gdeltproject.org/gdeltv2/other.export.CSV.zip")
        self.assertEqual(result.source_url, URL)
        self.assertEqual(result.timestamp.isoformat(), "2026-10-24T02:00:00+00:00")
        for text in ("", row + "\n" + row, row.replace("123", "0", 1), row.replace("a" * 32, "bad")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_latest_manifest(text)

    def test_latest_manifest_fetch_is_bounded(self):
        with patch.object(sample, "_open", return_value=io.BytesIO(b"x" * (64 * 1024 + 1))):
            with self.assertRaises(ValueError):
                sample.fetch_latest()

    def test_url_and_timestamp_validation(self):
        for url in (URL + "?", URL + "#x", URL.replace("data.", "evil."),
                    URL.replace("/gdeltv2/", "/gdeltv2/../"), URL.replace("020000", "020100"),
                    URL.replace("20261024", "20260230"), URL.replace(".org/", ".org:443/"),
                    URL.replace(".org/", ".org@evil.example/")):
            with self.subTest(url=url), self.assertRaises(ValueError):
                GkgBatchRef(url, 1, "a" * 32)
        with self.assertRaises(ValueError):
            sample._open(URL.replace("https:", "http:"))
        with self.assertRaises(ValueError):
            sample._NoRedirects().redirect_request(None, None, 302, "", {}, URL)

    def test_stream_download_integrity_and_cleanup(self):
        data = b"x" * 150000
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sample, "_open", return_value=io.BytesIO(data)):
                result = sample.download_sample(batch(data), Path(directory))
            self.assertEqual(Path(result["path"]).read_bytes(), data)
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
            for actual in (data[:-1], data + b"x", b"y" * len(data)):
                with patch.object(sample, "_open", return_value=io.BytesIO(actual)), self.assertRaises(ValueError):
                    sample.download_sample(batch(data), Path(directory))
                self.assertEqual(Path(result["path"]).read_bytes(), data)
                self.assertFalse(list(Path(directory).glob("*.part")))
            with patch.object(sample, "MAX_ZIP_BYTES", 1), patch.object(sample, "_open") as opener:
                with self.assertRaises(ValueError):
                    sample.download_sample(batch(data), Path(directory))
                opener.assert_not_called()

    def test_inspect_source_literals_widths_titles_and_preview_bounds(self):
        row = [""] * 27
        row[0], row[3], row[4] = 'id"literal\\', "example.com", "https://example.com/" + "x" * 500
        row[26] = "<PAGE_TITLE>&lt;b&gt;Title&lt;/b&gt; &amp; more</PAGE_TITLE>"
        text = "\t".join(row) + "\n" + "\t".join([""] * 27) + "\nshort\trow\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / (NAME + ".zip")
            path.write_bytes(zip_bytes(text))
            result = sample.inspect_sample(path)
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["column_counts"], {"2": 1, "27": 2})
        self.assertEqual(result["rows_with_title"], 1)
        self.assertEqual(result["previews"][0]["id"], row[0])
        self.assertEqual(result["previews"][0]["headline"], "Title & more")
        self.assertLessEqual(len(result["previews"][0]["url"]), 240)

    def test_archive_safety_caps_and_crc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / (NAME + ".zip")
            for name in ("../" + NAME, "/" + NAME, "folder/" + NAME, "other.csv"):
                path.write_bytes(zip_bytes("row\n", name))
                with self.subTest(name=name), self.assertRaises(ValueError):
                    sample.inspect_sample(path)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(NAME, "row")
                archive.writestr("other", "row")
            path.write_bytes(buffer.getvalue())
            with self.assertRaises(ValueError):
                sample.inspect_sample(path)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                link = zipfile.ZipInfo(NAME)
                link.external_attr = 0o120777 << 16
                archive.writestr(link, "target")
            path.write_bytes(buffer.getvalue())
            with self.assertRaises(ValueError):
                sample.inspect_sample(path)
            path.write_bytes(zip_bytes(b"\xff"))
            with self.assertRaises(UnicodeDecodeError):
                sample.inspect_sample(path)
            path.write_bytes(zip_bytes("row\n"))
            with patch.object(sample, "MAX_UNCOMPRESSED_BYTES", 1), self.assertRaises(ValueError):
                sample.inspect_sample(path)
            with patch.object(sample, "MAX_ROW_BYTES", 1), self.assertRaises(ValueError):
                sample.inspect_sample(path)
            damaged = bytearray(path.read_bytes())
            damaged[damaged.index(b"row\n")] ^= 1
            path.write_bytes(damaged)
            with self.assertRaises(zipfile.BadZipFile):
                sample.inspect_sample(path)

    def test_one_latest_end_to_end_offline(self):
        data = zip_bytes("id\tdomain\n")
        manifest = f"{len(data)} {hashlib.md5(data).hexdigest()} {URL}".encode()
        with tempfile.TemporaryDirectory() as directory, patch.object(
            sample, "_open", side_effect=[io.BytesIO(manifest), io.BytesIO(data)]
        ) as opener:
            result = sample.obtain_latest_sample(directory)
            self.assertEqual(result["rows"], 1)
            self.assertEqual([call.args[0] for call in opener.call_args_list], [sample.LATEST_URL, URL])

    def test_manual_dagster_job_without_gcp_environment_or_initialization(self):
        from jobs_orchestrator.definitions import defs
        from jobs_orchestrator.resources.gcp import GcpResource

        with patch.dict(os.environ, {"ENV": "prod", "DAGSTER_ENVIRONMENT": "prod", "SLACK_NOTIFICATIONS_ENABLED": "false"}, clear=True), patch.object(
            GcpResource, "setup_for_execution", side_effect=AssertionError("GCP initialized")
        ), patch("jobs_orchestrator.assets.gdelt_gkg.asset.obtain_latest_sample", return_value={
            "path": "/local/sample.zip", "rows": 1, "column_counts": {"27": 1}, "previews": []
        }) as obtain:
            result = defs.resolve_job_def("gdelt_gkg_sample_job").execute_in_process(
                run_config={"ops": {"gdelt_gkg_sample": {"config": {"output_dir": "/local"}}}}
            )
        self.assertTrue(result.success)
        obtain.assert_called_once_with("/local")
        self.assertEqual(len(result.get_asset_materialization_events()), 1)
        self.assertFalse(any(event.event_type_value == "HANDLED_OUTPUT" for event in result.all_events))


if __name__ == "__main__":
    unittest.main()
