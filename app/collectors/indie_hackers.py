from __future__ import annotations

from app.collectors.rss import RssCollector


class IndieHackersCollector(RssCollector):
    def __init__(self, feed_url: str, limit: int = 20):
        super().__init__("indie_hackers", feed_url, limit)
