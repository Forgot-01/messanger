import re
import time
from datetime import UTC, datetime

LINK_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"']", re.IGNORECASE)


def contains_link(content: str | None) -> bool:
    return content is not None and LINK_PATTERN.search(content) is not None


def now_utc() -> datetime:
    return datetime.now(UTC)


def fromtimestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, UTC)

def now_ms() -> int:
    return int(time.time() * 1000)

