from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session, sessionmaker

from app.bot.message_formatter import format_candidate_message
from app.bot.telegram_client import TelegramClient
from app.config import Settings
from app.pipeline import collect_all, prepare_next_candidate
from app.storage.repositories import has_been_sent_today, record_sent
from app.utils.time import start_of_local_day_utc

logger = logging.getLogger(__name__)


def build_scheduler(settings: Settings, session_factory: sessionmaker[Session]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        send_daily_case,
        CronTrigger(hour=settings.daily_send_hour, minute=settings.daily_send_minute, timezone=settings.timezone),
        args=[settings, session_factory],
        id="daily_ai_news",
        replace_existing=True,
    )
    return scheduler


async def send_daily_case(settings: Settings, session_factory: sessionmaker[Session]) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram credentials missing; daily send skipped")
        return
    await collect_all(settings, session_factory)
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    with session_factory() as session:
        if has_been_sent_today(session, start_of_local_day_utc(settings.timezone)) is not None:
            logger.info("Daily case already sent today")
            return
        candidate = prepare_next_candidate(session)
        if candidate is None:
            await client.send_html("오늘 발송할 적절한 AI/바이브코딩 사례를 찾지 못했습니다.")
            return
        message = format_candidate_message(candidate)
        telegram_message_id = await client.send_html(message)
        record_sent(session, candidate, message, telegram_message_id)
        session.commit()
