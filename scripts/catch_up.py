import argparse
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
    parser = argparse.ArgumentParser(description="Send multiple queued GPTERS case posts")
    parser.add_argument("--count", type=int, default=5, help="Number of messages to send")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    factory = create_session_factory(settings)
    saved = await collect_all(settings, factory)
    print(f"Collected/updated candidates: {saved}")

    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    with factory() as session:
        sent_count = 0
        for index in range(1, args.count + 1):
            candidate = prepare_next_candidate(session, settings)
            if candidate is None:
                if sent_count == 0:
                    await client.send_html(QUEUE_EXHAUSTED_MESSAGE)
                    print("Queue exhausted")
                else:
                    print("No more candidates available")
                break
            message = format_candidate_message(candidate)
            message_id = await client.send_html(message)
            record_sent(session, candidate, message, message_id)
            session.commit()
            sent_count += 1
            print(
                f"Sent {index}/{args.count}: candidate {candidate.id} "
                f"by {candidate.author} ({candidate.category})"
            )

        print(f"Catch-up complete: {sent_count} message(s) sent")


if __name__ == "__main__":
    asyncio.run(main())
