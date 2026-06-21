from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_in(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def start_of_local_day_utc(tz_name: str) -> datetime:
    local_now = now_in(tz_name)
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)
