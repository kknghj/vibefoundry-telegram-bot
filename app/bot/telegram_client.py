from __future__ import annotations

from telegram import Bot


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send_html(self, text: str) -> str | None:
        message = await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )
        return str(message.message_id)
