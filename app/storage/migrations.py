from __future__ import annotations

from app.config import get_settings
from app.storage.db import init_db


def run() -> None:
    init_db(get_settings())
