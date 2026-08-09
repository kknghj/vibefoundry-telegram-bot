import asyncio

from _bootstrap import setup_script

setup_script()

from app.bot.message_formatter import format_candidate_message
from app.bot.telegram_client import TelegramClient
from app.config import get_settings
from app.pipeline import QUEUE_EXHAUSTED_MESSAGE, collect_all, prepare_next_candidate
from app.storage.db import create_session_factory
from app.storage.repositories import record_sent


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    factory = create_session_factory(settings)
    await collect_all(settings, factory)
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    with factory() as session:
        candidate = prepare_next_candidate(session, settings)
        if candidate is None:
            await client.send_html(QUEUE_EXHAUSTED_MESSAGE)
            print("Queue exhausted")
            return
        message = format_candidate_message(candidate)
        message_id = await client.send_html(message)
        record_sent(session, candidate, message, message_id)
        session.commit()
        print(f"Sent candidate {candidate.id} by {candidate.author}")


if __name__ == "__main__":
    asyncio.run(main())
