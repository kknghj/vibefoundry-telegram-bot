from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.collectors.base import RawItem


class ProductHuntCollector:
    source_name = "product_hunt"
    source_type = "api"

    def __init__(self, token: str, limit: int = 20):
        self.token = token
        self.limit = limit

    async def collect(self) -> list[RawItem]:
        query = """
        query Posts($first: Int!) {
          posts(first: $first, order: NEWEST) {
            edges {
              node {
                id
                name
                tagline
                url
                votesCount
                commentsCount
                createdAt
                topics { edges { node { name } } }
              }
            }
          }
        }
        """
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.producthunt.com/v2/api/graphql",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"query": query, "variables": {"first": self.limit}},
            )
            response.raise_for_status()
        edges = response.json().get("data", {}).get("posts", {}).get("edges", [])
        items: list[RawItem] = []
        for edge in edges:
            node = edge.get("node") or {}
            topics = [t.get("node", {}).get("name") for t in node.get("topics", {}).get("edges", [])]
            items.append(
                RawItem(
                    source_name=self.source_name,
                    source_url=node.get("url") or "",
                    title=node.get("name") or "",
                    raw_text=node.get("tagline") or "",
                    published_at=_parse_iso(node.get("createdAt")),
                    engagement={
                        "votes": node.get("votesCount"),
                        "comments": node.get("commentsCount"),
                        "topics": [t for t in topics if t],
                    },
                    external_id=node.get("id"),
                )
            )
        return items


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
