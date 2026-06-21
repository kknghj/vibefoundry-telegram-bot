import asyncio

from _bootstrap import setup_script

setup_script()

from app.bot.message_formatter import format_candidate_message
from app.bot.telegram_client import TelegramClient
from app.config import get_settings
from app.pipeline import collect_all, prepare_next_candidate
from app.storage.db import create_session_factory
from app.storage.repositories import has_been_sent_today, record_sent
from app.utils.time import start_of_local_day_utc


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    factory = create_session_factory(settings)
    await collect_all(settings, factory)
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    with factory() as session:
        existing = has_been_sent_today(session, start_of_local_day_utc(settings.timezone))
        if existing is not None:
            print("Already sent today")
            return
        candidate = prepare_next_candidate(session)
        if candidate is None:
            await client.send_html("오늘 발송할 적절한 AI/바이브코딩 사례를 찾지 못했습니다.")
            print("No candidate available")
            return
        message = format_candidate_message(candidate)
        message_id = await client.send_html(message)
        record_sent(session, candidate, message, message_id)
        session.commit()
        print(f"Sent candidate {candidate.id}")


if __name__ == "__main__":
    asyncio.run(main())
