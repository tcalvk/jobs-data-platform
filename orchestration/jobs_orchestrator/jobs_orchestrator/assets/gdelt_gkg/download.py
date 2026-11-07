"""Only HTTP/download verification failures receive automatic retries."""

import hashlib
from http.client import HTTPException
from pathlib import Path
import time
from urllib.error import HTTPError, URLError

from . import sample
from .manifest import LATEST_URL, parse_latest_manifest


class DownloadFailure(ValueError):
    pass


def _retry(operation, sleep=time.sleep):
    for attempt in range(3):
        try:
            return operation()
        except HTTPError as exc:
            if exc.code not in (408, 429) and not 500 <= exc.code <= 599:
                raise DownloadFailure("Source HTTP request failed") from exc
            error = exc
        except (DownloadFailure, URLError, TimeoutError, ConnectionError, HTTPException) as exc:
            error = exc
        if attempt < 2:
            sleep(2 ** attempt)
    raise DownloadFailure("Download failed after three attempts") from error


def fetch_latest():
    def fetch():
        with sample._open(LATEST_URL) as response:
            body = response.read(65537)
        if len(body) > 65536:
            raise DownloadFailure("Manifest exceeds cap")
        return parse_latest_manifest(body.decode("utf-8"))
    return _retry(fetch)


def download_archive(batch, path: Path):
    def fetch():
        count = 0
        digest = hashlib.md5()
        with sample._open(batch.source_url) as response, path.open("wb") as target:
            length = response.headers.get("Content-Length") if hasattr(response, "headers") else None
            if length is not None and (not length.isdigit() or int(length) != batch.expected_size_bytes):
                raise DownloadFailure("Source Content-Length mismatch")
            while chunk := response.read(65536):
                count += len(chunk)
                if count > batch.expected_size_bytes:
                    raise DownloadFailure("Source size mismatch")
                digest.update(chunk)
                target.write(chunk)
        if count != batch.expected_size_bytes or digest.hexdigest() != batch.expected_md5:
            raise DownloadFailure("Source size/MD5 mismatch")
    _retry(fetch)
