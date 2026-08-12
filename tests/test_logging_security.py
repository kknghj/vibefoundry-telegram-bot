import logging

from app.config import Settings
from app.utils.logging import configure_logging


def test_http_client_request_urls_are_not_logged_at_info(tmp_path, monkeypatch):
    monkeypatch.setattr("app.utils.logging.ROOT_DIR", tmp_path)
    settings = Settings(
        telegram_bot_token=None,
        telegram_chat_id=None,
        database_url="sqlite:///:memory:",
        timezone="Asia/Seoul",
        send_hours=(8, 20),
        send_minute=0,
        log_level="INFO",
        openai_api_key=None,
        openai_model="gpt-4.1-mini",
        gpters_authors=("author",),
        gpters_published_after=__import__("datetime").datetime(2026, 7, 20),
    )

    configure_logging(settings)

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
