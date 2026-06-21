from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.storage.db import init_db


if __name__ == "__main__":
    init_db(get_settings())
    print("Database initialized")
