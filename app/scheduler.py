from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session, sessionmaker

from app.bot.message_formatter import format_candidate_message
from app.bot.telegram_client import TelegramClient
from app.config import Settings
from app.pipeline import QUEUE_EXHAUSTED_MESSAGE, collect_all, prepare_next_candidate
from app.storage.repositories import has_been_sent_since, record_sent
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

ExhaustedCallback = Callable[[], Awaitable[None]] | None


def build_scheduler(
    settings: Settings,
    session_factory: sessionmaker[Session],
    on_exhausted: ExhaustedCallback = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        send_scheduled_case,
        CronTrigger(hour=list(settings.send_hours), minute=settings.send_minute, timezone=settings.timezone),
        args=[settings, session_factory, on_exhausted],
        id="gpters_case_digest",
        replace_existing=True,
    )
    return scheduler


async def send_scheduled_case(
    settings: Settings,
    session_factory: sessionmaker[Session],
    on_exhausted: ExhaustedCallback = None,
) -> str:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram credentials missing; scheduled send skipped")
        return "skipped"

    await collect_all(settings, session_factory)
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    with session_factory() as session:
        # Guard against duplicate fire within the same morning/evening window.
        if has_been_sent_since(session, utcnow() - timedelta(hours=6)) is not None:
            logger.info("Case already sent in the current schedule window")
            return "already_sent"

        candidate = prepare_next_candidate(session, settings)
        if candidate is None:
            await client.send_html(QUEUE_EXHAUSTED_MESSAGE)
            session.commit()
            logger.info("GPTERS queue exhausted; requesting shutdown")
            if on_exhausted is not None:
                await on_exhausted()
            return "exhausted"

        message = format_candidate_message(candidate)
        telegram_message_id = await client.send_html(message)
        record_sent(session, candidate, message, telegram_message_id)
        session.commit()
        return "sent"
