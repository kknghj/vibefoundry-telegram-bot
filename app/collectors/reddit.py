from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

import logging

import httpx

from app.collectors.base import RawItem
from app.utils.text import compact_whitespace

logger = logging.getLogger(__name__)

REDDIT_USER_AGENT = "windows:telegram-ai-news:0.1 (by /u/telegramainewsbot)"
MIN_REQUEST_INTERVAL_SEC = 6.0
MAX_429_RETRIES = 5

_reddit_lock = asyncio.Lock()
_last_request_monotonic = 0.0


async def _reddit_get_json(client: httpx.AsyncClient, url: str) -> str:
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
                payload = json.loads(await _reddit_get_json(client, url))
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

    def __init__(self, subreddit: str, sort: str = "hot", limit: int = 15):
        self.source_name = f"reddit_{subreddit.lower()}"
        self.subreddit = subreddit
        self.sort = sort
        self.limit = limit
        self.json_url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"

    async def fetch_json_text(self, client: httpx.AsyncClient) -> str:
        return await _reddit_get_json(client, self.json_url)

    async def collect(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            payload = json.loads(await self.fetch_json_text(client))

        items: list[RawItem] = []
        for child in payload.get("data", {}).get("children", []):
            post = child.get("data") or {}
            post_id = post.get("id")
            if not post_id:
                continue
            permalink = post.get("permalink")
            link = f"https://www.reddit.com{permalink}" if permalink else post.get("url") or ""
            title = compact_whitespace(post.get("title") or "")
            selftext = compact_whitespace(post.get("selftext") or "")
            created = post.get("created_utc")
            published_at = (
                datetime.fromtimestamp(created, tz=timezone.utc) if isinstance(created, int | float) else None
            )
            items.append(
                RawItem(
                    source_name=self.source_name,
                    source_url=link,
                    title=title,
                    author=post.get("author"),
                    raw_text=selftext,
                    published_at=published_at,
                    engagement={
                        "ups": post.get("ups"),
                        "num_comments": post.get("num_comments"),
                        "score": post.get("score"),
                    },
                    external_id=post_id,
                )
            )
        return items
