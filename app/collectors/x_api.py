from __future__ import annotations

import httpx

from app.collectors.base import RawItem


class XApiCollector:
    source_name = "x"
    source_type = "api"

    def __init__(self, bearer_token: str, max_results: int = 10):
        self.bearer_token = bearer_token
        self.max_results = max_results
        self.query = '("vibe coding" OR "built with AI" OR "AI automation" OR "built this with Cursor" OR "ChatGPT built app") -is:retweet lang:en'

    async def collect(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.x.com/2/tweets/search/recent",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                params={
                    "query": self.query,
                    "max_results": self.max_results,
                    "tweet.fields": "created_at,public_metrics,author_id",
                },
            )
            response.raise_for_status()
        items: list[RawItem] = []
        for row in response.json().get("data", []):
            tweet_id = row.get("id")
            items.append(
                RawItem(
                    source_name=self.source_name,
                    source_url=f"https://x.com/i/web/status/{tweet_id}",
                    title=(row.get("text") or "")[:120],
                    author=row.get("author_id"),
                    raw_text=row.get("text") or "",
                    engagement=row.get("public_metrics") or {},
                    external_id=tweet_id,
                )
            )
        return items
