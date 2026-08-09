from __future__ import annotations

from datetime import datetime, timezone
import logging
import re

import httpx

from app.collectors.base import RawItem

logger = logging.getLogger(__name__)

BETTERMODE_GRAPHQL_URL = "https://api.bettermode.com/graphql"
GPTERS_HOME_URL = "https://www.gpters.org/"
NETWORK_ID = "sDly8LKFxJ"

DEFAULT_AUTHOR_MEMBER_IDS = {
    "자연어회계처리": "mIawQvprEj",
    "유피테르": "8vj7lvkHr7",
    "벤쿠버쪼": "25L3aBmMMe",
    "이생강": "58XkYVYc55",
    "Giacomo": "QYhKM8L4AC",
    "망원궁예": "c1P4XFX18K",
}


class GptersCollector:
    source_name = "gpters"
    source_type = "api"
    user_agent = "telegram-ai-news-bot/0.1"

    def __init__(
        self,
        authors: list[str],
        published_after: datetime,
        author_member_ids: dict[str, str] | None = None,
        page_size: int = 50,
        max_posts_per_author: int = 500,
    ):
        self.authors = authors
        self.published_after = (
            published_after
            if published_after.tzinfo is not None
            else published_after.replace(tzinfo=timezone.utc)
        )
        self.author_member_ids = author_member_ids or dict(DEFAULT_AUTHOR_MEMBER_IDS)
        self.page_size = page_size
        self.max_posts_per_author = max_posts_per_author

    async def collect(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            token = await self._guest_token(client)
            items: list[RawItem] = []
            for author in self.authors:
                member_id = self.author_member_ids.get(author)
                if not member_id:
                    member_id = await self._resolve_member_id(client, token, author)
                    if member_id:
                        self.author_member_ids[author] = member_id
                if not member_id:
                    logger.warning("GPTERS member id not found for author=%s", author)
                    continue
                posts = await self._member_posts(client, token, member_id)
                for post in posts:
                    item = self._to_raw_item(author, post)
                    if item is not None:
                        items.append(item)
            return items

    async def _guest_token(self, client: httpx.AsyncClient) -> str:
        response = await client.get(GPTERS_HOME_URL, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        match = re.search(r'"accessToken":"([^"]+)"', response.text)
        if not match:
            raise RuntimeError("GPTERS guest access token not found")
        return match.group(1)

    async def _gql(self, client: httpx.AsyncClient, token: str, query: str, variables: dict) -> dict:
        response = await client.post(
            BETTERMODE_GRAPHQL_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Tribe-Network-Id": NETWORK_ID,
                "User-Agent": self.user_agent,
            },
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"GPTERS GraphQL error: {payload['errors']}")
        return payload.get("data") or {}

    async def _resolve_member_id(self, client: httpx.AsyncClient, token: str, author: str) -> str | None:
        data = await self._gql(
            client,
            token,
            """
            query($query: String!, $limit: Int!) {
              searchMembers(query: $query, limit: $limit) {
                nodes { id name }
              }
            }
            """,
            {"query": author, "limit": 5},
        )
        nodes = ((data.get("searchMembers") or {}).get("nodes")) or []
        exact = next((node for node in nodes if node.get("name") == author), None)
        if exact:
            return exact.get("id")
        return nodes[0].get("id") if nodes else None

    async def _member_posts(self, client: httpx.AsyncClient, token: str, member_id: str) -> list[dict]:
        query = """
        query($memberId: ID!, $limit: Int!, $after: String) {
          memberPosts(memberId: $memberId, limit: $limit, after: $after, reverse: true) {
            nodes {
              id
              title
              relativeUrl
              url
              publishedAt
              createdAt
              shortContent
              space { name slug }
            }
            pageInfo { endCursor hasNextPage }
          }
        }
        """
        nodes: list[dict] = []
        after: str | None = None
        while len(nodes) < self.max_posts_per_author:
            data = await self._gql(
                client,
                token,
                query,
                {"memberId": member_id, "limit": self.page_size, "after": after},
            )
            page = data.get("memberPosts") or {}
            batch = page.get("nodes") or []
            if not batch:
                break
            nodes.extend(batch)
            # Posts are newest-first; stop early once we pass the cutoff.
            oldest = self._parse_dt(batch[-1].get("publishedAt") or batch[-1].get("createdAt"))
            if oldest is not None and oldest < self.published_after:
                break
            page_info = page.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")
            if not after:
                break
        return nodes

    def _to_raw_item(self, author: str, post: dict) -> RawItem | None:
        published_at = self._parse_dt(post.get("publishedAt") or post.get("createdAt"))
        if published_at is None or published_at < self.published_after:
            return None
        relative_url = post.get("relativeUrl") or ""
        url = post.get("url") or (f"https://www.gpters.org{relative_url}" if relative_url else "")
        if not url:
            return None
        title = (post.get("title") or "").strip()
        if not title:
            return None
        external_id = post.get("id") or url
        return RawItem(
            source_name=self.source_name,
            source_url=url,
            title=title,
            author=author,
            raw_text=(post.get("shortContent") or "").strip(),
            published_at=published_at,
            engagement={"space": (post.get("space") or {}).get("name")},
            external_id=str(external_id),
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
