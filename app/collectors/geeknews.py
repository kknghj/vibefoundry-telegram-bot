from __future__ import annotations

from app.collectors.rss import RssCollector


class GeekNewsCollector(RssCollector):
    def __init__(self, feed_url: str, limit: int = 20):
        super().__init__("geeknews", feed_url, limit)
