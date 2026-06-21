from __future__ import annotations

from app.collectors.rss import RssCollector


class RedditRssCollector(RssCollector):
    def __init__(self, subreddit: str, sort: str = "new", limit: int = 15):
        feed_url = f"https://www.reddit.com/r/{subreddit}/{sort}/.rss"
        super().__init__(source_name=f"reddit_{subreddit.lower()}", feed_url=feed_url, limit=limit)
        self.subreddit = subreddit
