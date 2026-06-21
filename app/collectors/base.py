from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class RawItem:
    source_name: str
    source_url: str
    title: str
    author: str | None = None
    raw_text: str = ""
    published_at: datetime | None = None
    engagement: dict[str, Any] = field(default_factory=dict)
    external_id: str | None = None


class Collector(Protocol):
    source_name: str
    source_type: str

    async def collect(self) -> list[RawItem]:
        ...
