from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session, sessionmaker

from app.bot.message_formatter import format_candidate_message
from app.bot.telegram_client import TelegramClient
from app.config import Settings
from app.pipeline import QUEUE_EXHAUSTED_MESSAGE, collect_all, prepare_next_candidate
from app.storage.repositories import has_been_sent_since, record_sent
from app.utils.time import now_in, utcnow

logger = logging.getLogger(__name__)

ExhaustedCallback = Callable[[], Awaitable[None]] | None


def latest_due_slot(settings: Settings, now_local: datetime | None = None) -> datetime | None:
    """Most recent scheduled send time that is already due in the local timezone."""
    local_now = now_local or now_in(settings.timezone)
    if local_now.tzinfo is None:
        raise ValueError("now_local must be timezone-aware")

    slots: list[datetime] = []
    for day_offset in (0, 1):
        day = local_now.date() - timedelta(days=day_offset)
        for hour in settings.send_hours:
            slot = datetime(
                day.year,
                day.month,
                day.day,
                hour,
                settings.send_minute,
                tzinfo=local_now.tzinfo,
            )
            if slot <= local_now:
                slots.append(slot)
    return max(slots) if slots else None


def build_scheduler(
    settings: Settings,
    session_factory: sessionmaker[Session],
    on_exhausted: ExhaustedCallback = None,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        send_scheduled_case,
        # CronTrigger stringifies the hour value; a list becomes "[8, 20]" and breaks parsing.
        CronTrigger(
            hour=",".join(str(hour) for hour in settings.send_hours),
            minute=settings.send_minute,
            timezone=settings.timezone,
        ),
        args=[settings, session_factory, on_exhausted],
        id="gpters_case_digest",
        replace_existing=True,
    )
    return scheduler


async def catch_up_if_missed(
    settings: Settings,
    session_factory: sessionmaker[Session],
    on_exhausted: ExhaustedCallback = None,
) -> str:
    """Send once on startup if the latest due schedule slot was missed while offline."""
    slot = latest_due_slot(settings)
    if slot is None:
        logger.info("Startup catch-up skipped: no due schedule slot yet")
        return "no_slot"

    slot_utc = slot.astimezone(timezone.utc)
    with session_factory() as session:
        if has_been_sent_since(session, slot_utc) is not None:
            logger.info("Startup catch-up skipped: already sent for slot %s", slot.isoformat())
            return "already_sent"

    logger.info("Startup catch-up: missed slot %s, sending now", slot.isoformat())
    return await send_scheduled_case(settings, session_factory, on_exhausted=on_exhausted)


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
        # Prefer the current due slot; fall back to a 6h window for safety.
        slot = latest_due_slot(settings)
        since = slot.astimezone(timezone.utc) if slot is not None else utcnow() - timedelta(hours=6)
        if has_been_sent_since(session, since) is not None:
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
