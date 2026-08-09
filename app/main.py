from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application, CommandHandler

from app.bot.handlers import BotHandlers
from app.config import get_settings
from app.scheduler import build_scheduler
from app.single_instance import acquire_lock
from app.storage.db import create_session_factory
from app.utils.logging import configure_logging

logger = logging.getLogger(__name__)


async def start_scheduler(application) -> None:
    application.bot_data["scheduler"].start()


async def stop_scheduler(application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    settings = get_settings()
    configure_logging(settings)
    acquire_lock()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run the bot")
    session_factory = create_session_factory(settings)
    handlers = BotHandlers(settings, session_factory)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(start_scheduler)
        .post_shutdown(stop_scheduler)
        .build()
    )

    async def on_exhausted() -> None:
        logger.info("Stopping application after GPTERS queue exhaustion")
        application.stop_running()

    scheduler = build_scheduler(settings, session_factory, on_exhausted=on_exhausted)
    application.bot_data["scheduler"] = scheduler
    application.add_handler(CommandHandler("today", handlers.today))
    application.add_handler(CommandHandler("next", handlers.next))
    application.add_handler(CommandHandler("sources", handlers.sources))
    application.run_polling()


if __name__ == "__main__":
    main()
