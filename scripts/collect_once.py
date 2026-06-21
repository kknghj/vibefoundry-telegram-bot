import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.pipeline import collect_all
from app.storage.db import create_session_factory


async def main() -> None:
    settings = get_settings()
    factory = create_session_factory(settings)
    saved = await collect_all(settings, factory)
    print(f"Saved candidates: {saved}")


if __name__ == "__main__":
    asyncio.run(main())
