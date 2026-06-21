from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session, sessionmaker

from app.collectors.geeknews import GeekNewsCollector
from app.collectors.gpters import GptersCollector
from app.collectors.indie_hackers import IndieHackersCollector
from app.collectors.manual_queue import ManualQueueCollector
from app.collectors.product_hunt import ProductHuntCollector
from app.collectors.reddit import RedditRssCollector
from app.collectors.x_api import XApiCollector
from app.collectors.youtube import YouTubeCollector
from app.config import Settings
from app.curation.selector import select_next_candidate
from app.curation.summarizer import enrich_candidate
from app.storage.models import Candidate
from app.storage.repositories import recent_sent_categories, save_collection_run, save_raw_item, upsert_source
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def build_collectors(settings: Settings, session: Session):
    collectors = [
        ManualQueueCollector(session),
        RedditRssCollector("SideProject"),
        RedditRssCollector("indiehackers"),
        RedditRssCollector("ChatGPTCoding"),
    ]
    if settings.geeknews_rss_url:
        collectors.append(GeekNewsCollector(settings.geeknews_rss_url))
    if settings.gpters_rss_url:
        collectors.append(GptersCollector(settings.gpters_rss_url))
    if settings.indie_hackers_rss_url:
        collectors.append(IndieHackersCollector(settings.indie_hackers_rss_url))
    if settings.youtube_api_key:
        collectors.append(YouTubeCollector(settings.youtube_api_key))
    if settings.product_hunt_token:
        collectors.append(ProductHuntCollector(settings.product_hunt_token))
    if settings.x_bearer_token:
        collectors.append(XApiCollector(settings.x_bearer_token))
    return collectors


async def collect_all(settings: Settings, session_factory: sessionmaker[Session]) -> int:
    total_saved = 0
    with session_factory() as session:
        collectors = build_collectors(settings, session)
        recent_categories = recent_sent_categories(session)
        configured_names = {collector.source_name for collector in collectors}
        for source_name, source_type, enabled in [
            ("youtube", "api", bool(settings.youtube_api_key)),
            ("product_hunt", "api", bool(settings.product_hunt_token)),
            ("x", "api", bool(settings.x_bearer_token)),
        ]:
            if source_name not in configured_names:
                upsert_source(session, source_name, source_type, enabled=False, error="API 토큰이 없어 비활성화됨")
        session.commit()
        for collector in collectors:
            started = utcnow()
            fetched = 0
            saved = 0
            try:
                items = await _collect_with_retry(collector)
                fetched = len(items)
                for item in items:
                    candidate = save_raw_item(session, item, recent_categories)
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
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(2 * (attempt + 1))
    raise last_error or RuntimeError("unknown collector error")


def prepare_next_candidate(session: Session) -> Candidate | None:
    candidate = select_next_candidate(session)
    if candidate is None:
        return None
    enrich_candidate(candidate)
    session.commit()
    return candidate
