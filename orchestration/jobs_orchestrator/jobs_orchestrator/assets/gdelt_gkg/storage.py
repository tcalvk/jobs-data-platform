"""Create-only GCS persistence with explicit verification and no SDK retries."""

import hashlib
from pathlib import Path
import re

from google.api_core.exceptions import NotFound, PreconditionFailed


class StorageConflict(ValueError):
    pass


def fingerprints(path: Path) -> dict:
    sha, md5 = hashlib.sha256(), hashlib.md5()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(65536):
            size += len(chunk)
            sha.update(chunk)
            md5.update(chunk)
    return {"size_bytes": size, "sha256": sha.hexdigest(), "md5": md5.hexdigest()}


class ArchiveStore:
    def __init__(self, client, bucket: str, directory: Path):
        self.client = client
        self.bucket = client.bucket(bucket)
        self.directory = directory

    def names(self, prefix):
        return [b.name for b in self.client.list_blobs(self.bucket, prefix=prefix, retry=None)]

    def get(self, name):
        blob = self.bucket.blob(name)
        try:
            blob.reload(retry=None)
            return blob
        except NotFound:
            return None

    def read(self, blob, path):
        blob.download_to_filename(str(path), if_generation_match=blob.generation, retry=None)
        actual = fingerprints(path)
        if actual["size_bytes"] != int(blob.size) or (blob.metadata or {}).get("sha256") != actual["sha256"]:
            raise StorageConflict("Object checksum/size conflict")
        return actual

    def artifact(self, blob):
        return {"uri": f"gs://{self.bucket.name}/{blob.name}", "size_bytes": int(blob.size),
                "sha256": blob.metadata["sha256"], "generation": str(blob.generation)}

    def verify_artifact(self, artifact):
        """Check a committed artifact's immutable identity without payload reads.

        Partial recovery and create/copy verification deliberately use read(),
        which verifies full bytes instead of trusting a completion receipt.
        """
        prefix = f"gs://{self.bucket.name}/"
        if (not isinstance(artifact, dict)
                or not isinstance(artifact.get("uri"), str)
                or not artifact["uri"].startswith(prefix)
                or type(artifact.get("size_bytes")) is not int
                or artifact["size_bytes"] < 0
                or not isinstance(artifact.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])
                or not isinstance(artifact.get("generation"), str)
                or not re.fullmatch(r"[1-9][0-9]*", artifact["generation"])):
            raise StorageConflict("Invalid receipt artifact")
        blob = self.get(artifact["uri"][len(prefix):])
        if blob is None or not blob.metadata or blob.metadata.get("sha256") != artifact["sha256"] or self.artifact(blob) != artifact:
            raise StorageConflict("Receipt artifact missing or changed")
        return blob

    def put(self, name, path, metadata):
        actual = fingerprints(path)
        metadata = {**metadata, "sha256": actual["sha256"]}
        blob = self.bucket.blob(name)
        blob.metadata = metadata
        try:
            blob.upload_from_filename(str(path), if_generation_match=0, retry=None)
        except PreconditionFailed:
            pass
        blob = self.get(name)
        if blob is None or blob.metadata != metadata:
            raise StorageConflict("Existing object metadata conflicts")
        found = self.read(blob, self.directory / "verify")
        if found != actual:
            raise StorageConflict("Existing object bytes conflict")
        return blob

    def delete(self, blob):
        try:
            blob.delete(if_generation_match=blob.generation, retry=None)
        except NotFound:
            # Another reconciler may already have deleted this exact raw copy.
            pass
