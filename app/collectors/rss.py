from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging

import feedparser
import httpx

from app.collectors.base import RawItem
from app.utils.text import compact_whitespace, strip_html

logger = logging.getLogger(__name__)


class RssCollector:
    source_type = "rss"

    def __init__(self, source_name: str, feed_url: str, limit: int = 20):
        self.source_name = source_name
        self.feed_url = feed_url
        self.limit = limit

    async def collect(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.feed_url, headers={"User-Agent": "telegram-ai-news-bot/0.1"})
            response.raise_for_status()
        parsed = feedparser.parse(response.text)
        items: list[RawItem] = []
        for entry in parsed.entries[: self.limit]:
            link = entry.get("link") or ""
            title = compact_whitespace(entry.get("title") or "")
            summary = compact_whitespace(strip_html(entry.get("summary") or entry.get("description") or ""))
            author = entry.get("author")
            published_at = _parse_date(entry.get("published") or entry.get("updated"))
            items.append(
                RawItem(
                    source_name=self.source_name,
                    source_url=link,
                    title=title,
                    author=author,
                    raw_text=summary,
                    published_at=published_at,
                    engagement={},
                    external_id=entry.get("id") or link,
                )
            )
        return items


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        logger.debug("Failed to parse RSS date: %s", value, exc_info=True)
        return None
