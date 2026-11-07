"""Deterministic structural-only JSONL staging; no partial publication."""

import gzip
import json
from pathlib import Path
import zipfile
import zlib

from .contract import Contract
from .manifest import GkgBatchRef
from .sample import MAX_ROW_BYTES, MAX_UNCOMPRESSED_BYTES, MAX_ZIP_BYTES


class ContentRejected(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def stage_parsed(raw: Path, output: Path, batch: GkgBatchRef, contract: Contract) -> int:
    count = total = 0
    try:
        if raw.stat().st_size > MAX_ZIP_BYTES:
            raise ContentRejected("compressed_size_cap")
        with zipfile.ZipFile(raw) as archive:
            members = archive.infolist()
            expected = batch.source_url.rsplit("/", 1)[1].removesuffix(".zip")
            if len(members) != 1 or members[0].filename != expected:
                raise ContentRejected("unsafe_zip")
            member = members[0]
            mode = member.external_attr >> 16
            if member.is_dir() or member.flag_bits & 1 or (mode & 0o170000) not in (0, 0o100000):
                raise ContentRejected("unsafe_zip")
            if member.file_size > MAX_UNCOMPRESSED_BYTES:
                raise ContentRejected("uncompressed_size_cap")
            with archive.open(member) as source, output.open("wb") as target:
                with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as sink:
                    while raw_line := source.readline(MAX_ROW_BYTES + 1):
                        total += len(raw_line)
                        if len(raw_line) > MAX_ROW_BYTES:
                            raise ContentRejected("row_size_cap")
                        if total > MAX_UNCOMPRESSED_BYTES:
                            raise ContentRejected("uncompressed_size_cap")
                        line = raw_line.removesuffix(b"\n")
                        if raw_line.endswith(b"\n"):
                            line = line.removesuffix(b"\r")
                        fields = line.decode("utf-8").split("\t")
                        if len(fields) != 27:
                            raise ContentRejected("field_count")
                        sink.write(json_bytes({
                            "contract_version": contract.version,
                            "batch_id": batch.timestamp.strftime("%Y%m%d%H%M%S") + ":gkg:english",
                            "batch_timestamp_utc": batch.timestamp.isoformat().replace("+00:00", "Z"),
                            "source_columns": dict(zip(contract.columns, fields)),
                        }) + b"\n")
                        count += 1
        return count
    except UnicodeDecodeError as exc:
        raise ContentRejected("invalid_utf8") from exc
    except (zipfile.BadZipFile, EOFError, zlib.error, NotImplementedError, RuntimeError) as exc:
        raise ContentRejected("invalid_zip") from exc
