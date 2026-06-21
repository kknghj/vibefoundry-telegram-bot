from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    database_url: str
    timezone: str
    daily_send_hour: int
    daily_send_minute: int
    log_level: str
    youtube_api_key: str | None
    product_hunt_token: str | None
    x_bearer_token: str | None
    gpters_rss_url: str | None
    geeknews_rss_url: str | None
    indie_hackers_rss_url: str | None

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


def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=_optional("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_optional("TELEGRAM_CHAT_ID"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/telegram_ai_news.db"),
        timezone=os.getenv("TIMEZONE", "Asia/Seoul"),
        daily_send_hour=int(os.getenv("DAILY_SEND_HOUR", "8")),
        daily_send_minute=int(os.getenv("DAILY_SEND_MINUTE", "0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        youtube_api_key=_optional("YOUTUBE_API_KEY"),
        product_hunt_token=_optional("PRODUCT_HUNT_TOKEN"),
        x_bearer_token=_optional("X_BEARER_TOKEN"),
        gpters_rss_url=_optional("GPTERS_RSS_URL"),
        geeknews_rss_url=_optional("GEEKNEWS_RSS_URL") or "https://news.hada.io/rss/news",
        indie_hackers_rss_url=_optional("INDIE_HACKERS_RSS_URL"),
    )
