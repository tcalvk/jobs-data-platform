"""Select the English GKG row from the fixed latest-batch manifest."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re

LATEST_URL = "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
ARCHIVE_URL = re.compile(
    r"https?://data\.gdeltproject\.org/gdeltv2/([0-9]{14})\.gkg\.csv\.zip"
)


@dataclass(frozen=True)
class GkgBatchRef:
    source_url: str
    expected_size_bytes: int
    expected_md5: str

    def __post_init__(self):
        match = ARCHIVE_URL.fullmatch(self.source_url)
        if not match:
            raise ValueError("archive URL outside strict GDELT allowlist")
        date = datetime.strptime(match[1], "%Y%m%d%H%M%S")
        if date.minute % 15 or date.second:
            raise ValueError("batch must be a UTC quarter-hour")
        if type(self.expected_size_bytes) is not int or self.expected_size_bytes <= 0:
            raise ValueError("expected size must be positive")
        if not re.fullmatch(r"[0-9a-fA-F]{32}", self.expected_md5):
            raise ValueError("invalid MD5")
        object.__setattr__(self, "source_url", self.source_url.replace("http:", "https:", 1))
        object.__setattr__(self, "expected_md5", self.expected_md5.lower())

    @property
    def timestamp(self) -> datetime:
        stamp = self.source_url.rsplit("/", 1)[1][:14]
        return datetime.strptime(stamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def parse_latest_manifest(text: str) -> GkgBatchRef:
    candidates = []
    for line in text.splitlines():
        fields = line.split()
        if fields and fields[-1].endswith(".gkg.csv.zip"):
            if len(fields) != 3:
                raise ValueError("malformed latest GKG row")
            size, md5, url = fields
            if not re.fullmatch(r"[0-9]+", size):
                raise ValueError("invalid size")
            candidates.append(GkgBatchRef(url, int(size), md5))
    if len(candidates) != 1:
        raise ValueError("expected exactly one English GKG row")
    return candidates[0]
