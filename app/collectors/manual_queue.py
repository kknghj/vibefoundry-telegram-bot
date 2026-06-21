from __future__ import annotations

from sqlalchemy.orm import Session

from app.collectors.base import RawItem
from app.storage.models import ManualQueue


class ManualQueueCollector:
    source_name = "manual_queue"
    source_type = "manual"

    def __init__(self, session: Session):
        self.session = session

    async def collect(self) -> list[RawItem]:
        rows = (
            self.session.query(ManualQueue)
            .filter(ManualQueue.status == "new")
            .order_by(ManualQueue.created_at.asc())
            .limit(20)
            .all()
        )
        items: list[RawItem] = []
        for row in rows:
            items.append(
                RawItem(
                    source_name=row.source_name or self.source_name,
                    source_url=row.url,
                    title=row.note or row.url,
                    raw_text=row.note or "",
                    external_id=f"manual:{row.id}",
                )
            )
            row.status = "collected"
        self.session.commit()
        return items
