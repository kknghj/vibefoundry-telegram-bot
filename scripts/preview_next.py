from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot.message_formatter import format_candidate_message
from app.config import get_settings
from app.pipeline import prepare_next_candidate
from app.storage.db import create_session_factory


if __name__ == "__main__":
    settings = get_settings()
    factory = create_session_factory(settings)
    with factory() as session:
        candidate = prepare_next_candidate(session)
        if candidate is None:
            print("No candidate available")
        else:
            print(format_candidate_message(candidate, preview=True))
