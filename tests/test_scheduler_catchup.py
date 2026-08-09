from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import Settings
from app.scheduler import latest_due_slot


def _settings(**overrides) -> Settings:
    base = dict(
        telegram_bot_token=None,
        telegram_chat_id=None,
        database_url="sqlite:///:memory:",
        timezone="Asia/Seoul",
        send_hours=(8, 20),
        send_minute=0,
        log_level="INFO",
        openai_api_key=None,
        openai_model="gpt-4.1-mini",
        gpters_authors=("작가",),
        gpters_published_after=datetime(2026, 7, 20, tzinfo=ZoneInfo("Asia/Seoul")),
    )
    base.update(overrides)
    return Settings(**base)


def test_latest_due_slot_before_morning():
    settings = _settings()
    now = datetime(2026, 8, 9, 7, 30, tzinfo=ZoneInfo("Asia/Seoul"))
    slot = latest_due_slot(settings, now)
    assert slot == datetime(2026, 8, 8, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def test_latest_due_slot_after_morning():
    settings = _settings()
    now = datetime(2026, 8, 9, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    slot = latest_due_slot(settings, now)
    assert slot == datetime(2026, 8, 9, 8, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def test_latest_due_slot_after_evening():
    settings = _settings()
    now = datetime(2026, 8, 9, 21, 15, tzinfo=ZoneInfo("Asia/Seoul"))
    slot = latest_due_slot(settings, now)
    assert slot == datetime(2026, 8, 9, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def test_latest_due_slot_exactly_on_schedule():
    settings = _settings()
    now = datetime(2026, 8, 9, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    slot = latest_due_slot(settings, now)
    assert slot == datetime(2026, 8, 9, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))
