"""Download exactly one latest ZIP and inspect it, without Dagster or cloud clients."""

import argparse
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
from urllib.request import HTTPRedirectHandler, build_opener
import zipfile

from .manifest import GkgBatchRef, LATEST_URL, parse_latest_manifest

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_ROW_BYTES = 2 * 1024 * 1024
DEFAULT_OUTPUT_DIR = "downloads/gdelt_gkg"


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("GDELT redirects are not allowed")


def _open(url):
    # Only the fixed manifest or validated canonical archive URL reaches here.
    if url != LATEST_URL:
        validated = GkgBatchRef(url, 1, "0" * 32)
        if validated.source_url != url:
            raise ValueError("HTTPS required")
    return build_opener(_NoRedirects()).open(url, timeout=60)


def fetch_latest() -> GkgBatchRef:
    with _open(LATEST_URL) as response:
        body = response.read(64 * 1024 + 1)
    if len(body) > 64 * 1024:
        raise ValueError("latest manifest too large")
    return parse_latest_manifest(body.decode("utf-8"))


def download_sample(batch: GkgBatchRef, output_dir: Path) -> dict:
    if batch.expected_size_bytes > MAX_ZIP_BYTES:
        raise ValueError("ZIP exceeds compressed size cap")
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / batch.source_url.rsplit("/", 1)[1]
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    count = 0
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_dir, suffix=".part", delete=False) as target:
            temporary = Path(target.name)
            with _open(batch.source_url) as response:
                while chunk := response.read(64 * 1024):
                    count += len(chunk)
                    if count > min(MAX_ZIP_BYTES, batch.expected_size_bytes):
                        raise ValueError("ZIP exceeds expected size or cap")
                    md5.update(chunk)
                    sha256.update(chunk)
                    target.write(chunk)
        if count != batch.expected_size_bytes or md5.hexdigest() != batch.expected_md5:
            raise ValueError("ZIP size/MD5 mismatch")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"path": str(path), "bytes": count, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def _preview(value: str) -> str:
    # Plain text only; no source HTML/control characters in Dagster metadata.
    value = html.unescape(value[:4096])
    value = re.sub(r"<[^>]*>", "", value)
    return " ".join("".join(c for c in value if c.isprintable() or c.isspace()).split())[:240]


def inspect_sample(path: Path) -> dict:
    """Count source rows/widths; preview only ID/domain/URL/optional PAGE_TITLE."""
    path = Path(path)
    widths, previews = Counter(), []
    rows = titles = total = 0
    old_field_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(MAX_ROW_BYTES)
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            expected = path.name.removesuffix(".zip")
            if len(members) != 1 or members[0].filename != expected:
                raise ValueError("ZIP must contain only its expected flat CSV member")
            member = members[0]
            mode = member.external_attr >> 16
            if member.is_dir() or (mode & 0o170000) not in (0, 0o100000):
                raise ValueError("ZIP member must be a regular file")
            if member.file_size > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("ZIP exceeds uncompressed cap")
            # Reading to EOF verifies CRC; no extraction and no article fetching.
            with archive.open(member) as source:
                while raw := source.readline(MAX_ROW_BYTES + 1):
                    total += len(raw)
                    if len(raw) > MAX_ROW_BYTES or total > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError("uncompressed data exceeds inspection cap")
                    row = next(csv.reader([raw.decode("utf-8").rstrip("\r\n")], delimiter="\t", quoting=csv.QUOTE_NONE))
                    rows += 1
                    widths[len(row)] += 1
                    title = re.search(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", row[26], re.DOTALL) if len(row) >= 27 else None
                    titles += bool(title and title[1].strip())
                    if len(previews) < 3:
                        previews.append({
                            "id": _preview(row[0]) if row else "",
                            "domain": _preview(row[3]) if len(row) > 3 else "",
                            "url": _preview(row[4]) if len(row) > 4 else "",
                            "headline": _preview(title[1]) if title else "",
                        })
    finally:
        csv.field_size_limit(old_field_limit)
    return {
        "rows": rows, "column_counts": {str(k): v for k, v in sorted(widths.items())},
        "rows_with_title": titles, "uncompressed_bytes": total, "previews": previews,
    }


def obtain_latest_sample(output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
    batch = fetch_latest()
    downloaded = download_sample(batch, Path(output_dir))
    return {
        **downloaded, "source_url": batch.source_url,
        "batch_timestamp_utc": batch.timestamp.isoformat(),
        "expected_bytes": batch.expected_size_bytes, "expected_md5": batch.expected_md5,
        **inspect_sample(Path(downloaded["path"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(json.dumps(obtain_latest_sample(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
