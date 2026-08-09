from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DEFAULT_GPTERS_AUTHORS = [
    "자연어회계처리",
    "유피테르",
    "벤쿠버쪼",
    "이생강",
    "Giacomo",
    "망원궁예",
]


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    database_url: str
    timezone: str
    send_hours: tuple[int, ...]
    send_minute: int
    log_level: str
    openai_api_key: str | None
    openai_model: str
    gpters_authors: tuple[str, ...]
    gpters_published_after: datetime

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        raw_path = self.database_url.removeprefix(prefix)
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path


def _optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _parse_send_hours(raw: str | None) -> tuple[int, ...]:
    if not raw or not raw.strip():
        return (8, 20)
    hours = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        hour = int(part)
        if hour < 0 or hour > 23:
            raise ValueError(f"Invalid SEND_HOURS value: {hour}")
        hours.append(hour)
    return tuple(hours or [8, 20])


def _parse_authors(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return tuple(DEFAULT_GPTERS_AUTHORS)
    authors = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(authors or DEFAULT_GPTERS_AUTHORS)


def _parse_published_after(raw: str | None, timezone_name: str) -> datetime:
    value = (raw or "2026-07-20").strip()
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        # "2026-07-20 이후" = that local calendar day 00:00 inclusive.
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed


def get_settings() -> Settings:
    timezone_name = os.getenv("TIMEZONE", "Asia/Seoul")
    # Backward-compatible single-hour env still works, but twice-daily is default.
    legacy_hour = os.getenv("DAILY_SEND_HOUR")
    send_hours_raw = os.getenv("SEND_HOURS")
    if send_hours_raw is None and legacy_hour is not None:
        send_hours_raw = f"{legacy_hour},20"

    return Settings(
        telegram_bot_token=_optional("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_optional("TELEGRAM_CHAT_ID"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/telegram_ai_news.db"),
        timezone=timezone_name,
        send_hours=_parse_send_hours(send_hours_raw),
        send_minute=int(os.getenv("SEND_MINUTE", os.getenv("DAILY_SEND_MINUTE", "0"))),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openai_api_key=_optional("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        gpters_authors=_parse_authors(_optional("GPTERS_AUTHORS")),
        gpters_published_after=_parse_published_after(_optional("GPTERS_PUBLISHED_AFTER"), timezone_name),
    )
