from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.message_formatter import format_candidate_message
from app.config import Settings
from app.pipeline import collect_all, prepare_next_candidate
from app.storage.models import Source
from app.storage.repositories import has_been_sent_today, record_sent
from app.utils.time import start_of_local_day_utc


class BotHandlers:
    def __init__(self, settings: Settings, session_factory: sessionmaker[Session]):
        self.settings = settings
        self.session_factory = session_factory

    async def today(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await collect_all(self.settings, self.session_factory)
        with self.session_factory() as session:
            existing = has_been_sent_today(session, start_of_local_day_utc(self.settings.timezone))
            if existing is not None:
                await update.effective_message.reply_text(
                    "오늘 이미 발송한 사례가 있습니다.\n\n" + existing.message_text,
                    parse_mode="HTML",
                )
                return
            candidate = prepare_next_candidate(session)
            if candidate is None:
                await update.effective_message.reply_text("오늘 발송할 적절한 후보를 찾지 못했습니다.")
                return
            message = format_candidate_message(candidate)
            sent = await update.effective_message.reply_text(message, parse_mode="HTML", disable_web_page_preview=False)
            record_sent(session, candidate, message, str(sent.message_id))
            session.commit()

    async def next(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await collect_all(self.settings, self.session_factory)
        with self.session_factory() as session:
            candidate = prepare_next_candidate(session)
            if candidate is None:
                await update.effective_message.reply_text("현재 미리볼 수 있는 후보가 없습니다.")
                return
            await update.effective_message.reply_text(
                format_candidate_message(candidate, preview=True),
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

    async def sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        with self.session_factory() as session:
            rows = session.scalars(select(Source).order_by(Source.name.asc())).all()
        if not rows:
            await update.effective_message.reply_text("아직 기록된 수집 소스 상태가 없습니다. /next 또는 /today를 먼저 실행하세요.")
            return
        lines = ["수집 소스 상태"]
        for row in rows:
            status = "ON" if row.enabled else "OFF"
            last = row.last_success_at or row.last_checked_at
            err = f" / 오류: {row.last_error[:80]}" if row.last_error else ""
            lines.append(f"- {row.name} ({row.type}) {status} / 최근: {last}{err}")
        await update.effective_message.reply_text("\n".join(lines))
