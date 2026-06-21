from __future__ import annotations

import httpx

from app.collectors.base import RawItem


class YouTubeCollector:
    source_name = "youtube"
    source_type = "api"

    def __init__(self, api_key: str, max_results: int = 10):
        self.api_key = api_key
        self.max_results = max_results
        self.queries = [
            "AI automation case study",
            "vibe coding app",
            "built an app with AI",
            "no code AI automation",
            "Cursor AI project",
        ]

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for query in self.queries:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "type": "video",
                        "order": "date",
                        "q": query,
                        "maxResults": self.max_results,
                        "key": self.api_key,
                    },
                )
                response.raise_for_status()
                for row in response.json().get("items", []):
                    video_id = row.get("id", {}).get("videoId")
                    snippet = row.get("snippet", {})
                    if not video_id:
                        continue
                    items.append(
                        RawItem(
                            source_name=self.source_name,
                            source_url=f"https://www.youtube.com/watch?v={video_id}",
                            title=snippet.get("title") or "",
                            author=snippet.get("channelTitle"),
                            raw_text=snippet.get("description") or "",
                            engagement={"query": query},
                            external_id=video_id,
                        )
                    )
        return items
