from _bootstrap import setup_script

setup_script()

from app.config import get_settings
from app.storage.db import init_db


if __name__ == "__main__":
    init_db(get_settings())
    print("Database initialized")
