from __future__ import annotations

import asyncio
import json
import re
import time

import logging

import feedparser
import httpx

from app.collectors.base import RawItem
from app.collectors.rss import _parse_date
from app.utils.text import compact_whitespace, strip_html

logger = logging.getLogger(__name__)

REDDIT_USER_AGENT = "windows:telegram-ai-news:0.1 (by /u/telegramainewsbot)"
MIN_REQUEST_INTERVAL_SEC = 6.0
MAX_429_RETRIES = 5

_reddit_lock = asyncio.Lock()
_last_request_monotonic = 0.0


async def _reddit_get(client: httpx.AsyncClient, url: str) -> str:
    global _last_request_monotonic

    async with _reddit_lock:
        elapsed = time.monotonic() - _last_request_monotonic
        if elapsed < MIN_REQUEST_INTERVAL_SEC:
            await asyncio.sleep(MIN_REQUEST_INTERVAL_SEC - elapsed)

        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(MAX_429_RETRIES):
            response = await client.get(url, headers={"User-Agent": REDDIT_USER_AGENT})
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 15 * (attempt + 1)))
                last_error = httpx.HTTPStatusError(
                    f"429 Too Many Requests for {url}",
                    request=response.request,
                    response=response,
                )
                await asyncio.sleep(retry_after)
                continue
            response.raise_for_status()
            _last_request_monotonic = time.monotonic()
            return response.text

        raise last_error or RuntimeError(f"reddit request failed: {url}")


async def fetch_post_engagement(post_ids: list[str], batch_size: int = 10) -> dict[str, dict]:
    if not post_ids:
        return {}
    normalized: list[str] = []
    for post_id in post_ids:
        normalized.append(post_id if post_id.startswith("t3_") else f"t3_{post_id}")

    result: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for offset in range(0, len(normalized), batch_size):
            batch = normalized[offset:offset + batch_size]
            url = f"https://www.reddit.com/api/info.json?id={','.join(batch)}"
            try:
                payload = json.loads(await _reddit_get(client, url))
            except httpx.HTTPError as exc:
                logger.warning("Reddit engagement refresh failed for batch %d: %s", offset // batch_size + 1, exc)
                continue
            for child in payload.get("data", {}).get("children", []):
                post = child.get("data") or {}
                reddit_id = post.get("id")
                if not reddit_id:
                    continue
                result[reddit_id] = {
                    "ups": post.get("ups"),
                    "num_comments": post.get("num_comments"),
                    "score": post.get("score"),
                }
    return result


class RedditRssCollector:
    source_type = "rss"
    user_agent = REDDIT_USER_AGENT

    def __init__(self, subreddit: str, sort: str = "hot", limit: int = 25):
        self.source_name = f"reddit_{subreddit.lower()}"
        self.subreddit = subreddit
        self.sort = sort
        self.limit = limit
        self.feed_url = f"https://www.reddit.com/r/{subreddit}/{sort}.rss?limit={limit}"

    async def fetch_feed_text(self, client: httpx.AsyncClient) -> str:
        return await _reddit_get(client, self.feed_url)

    async def collect(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            feed_text = await self.fetch_feed_text(client)
        parsed = feedparser.parse(feed_text)
        items: list[RawItem] = []
        for entry in parsed.entries[: self.limit]:
            link = entry.get("link") or ""
            post_id = _reddit_post_id(link, entry.get("id"))
            if not post_id:
                continue
            title = compact_whitespace(entry.get("title") or "")
            summary = compact_whitespace(strip_html(entry.get("summary") or entry.get("description") or ""))
            author = _reddit_author(entry.get("author"))
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
                    external_id=post_id,
                )
            )
        return items


def _reddit_post_id(link: str, entry_id: str | None) -> str | None:
    match = re.search(r"/comments/([a-z0-9]+)/", link, re.IGNORECASE)
    if match:
        return match.group(1)
    if entry_id:
        return entry_id.rsplit("/", 1)[-1]
    return None


def _reddit_author(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("/u/").strip()
