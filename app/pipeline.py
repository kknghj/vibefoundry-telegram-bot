from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.collectors.gpters import GptersCollector
from app.config import Settings
from app.curation.selector import select_random_gpters_candidate
from app.curation.summarizer import enrich_candidate, is_delivery_ready, needs_translation_refresh
from app.storage.models import Candidate
from app.storage.repositories import save_collection_run, save_raw_item, upsert_source
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

QUEUE_EXHAUSTED_MESSAGE = (
    "알림할 지피터스 사례글이 모두 소진되었습니다. "
    "지정한 작성자·기간 조건을 만족하는 미발송 게시글이 없어 봇을 종료합니다."
)


def build_collectors(settings: Settings):
    return [
        GptersCollector(
            authors=list(settings.gpters_authors),
            published_after=settings.gpters_published_after,
        )
    ]


async def collect_all(settings: Settings, session_factory: sessionmaker[Session]) -> int:
    total_saved = 0
    with session_factory() as session:
        collectors = build_collectors(settings)
        for collector in collectors:
            started = utcnow()
            fetched = 0
            saved = 0
            try:
                items = await _collect_with_retry(collector)
                fetched = len(items)
                for item in items:
                    candidate = save_raw_item(session, item, force_accept=True)
                    if candidate is not None:
                        saved += 1
                upsert_source(session, collector.source_name, collector.source_type, enabled=True)
                save_collection_run(session, collector.source_name, "success", started, fetched, saved)
                session.commit()
            except Exception as exc:
                logger.exception("Collector failed: %s", collector.source_name)
                session.rollback()
                upsert_source(session, collector.source_name, collector.source_type, enabled=True, error=str(exc))
                save_collection_run(session, collector.source_name, "failed", started, fetched, saved, str(exc))
                session.commit()
            total_saved += saved
    return total_saved


async def _collect_with_retry(collector, retries: int = 3):
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return await collector.collect()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", 30 * (attempt + 1)))
                await asyncio.sleep(retry_after)
                continue
            await asyncio.sleep(2 * (attempt + 1))
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(2 * (attempt + 1))
    raise last_error or RuntimeError("unknown collector error")


def prepare_next_candidate(session: Session, settings: Settings) -> Candidate | None:
    attempts = 0
    exclude_ids: set[int] = set()
    while attempts < 20:
        attempts += 1
        candidate = select_random_gpters_candidate(
            session,
            authors=settings.gpters_authors,
            published_after=settings.gpters_published_after,
            exclude_ids=exclude_ids,
        )
        if candidate is None:
            return None
        exclude_ids.add(candidate.id)
        enrich_candidate(candidate, force=needs_translation_refresh(candidate))
        if is_delivery_ready(candidate):
            return candidate
        candidate.status = "rejected"
        candidate.reject_reason = "한국어 번역 품질 검사 실패"
        logger.warning("Rejected candidate %s due to Korean translation quality check", candidate.id)
        session.commit()
    return None
