import re
from datetime import UTC, datetime

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_slug(value: str) -> bool:
    return bool(SLUG_RE.fullmatch(value))


def now() -> datetime:
    return datetime.now(UTC)
