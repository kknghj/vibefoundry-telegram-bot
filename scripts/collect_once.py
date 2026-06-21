import asyncio

from _bootstrap import setup_script

setup_script()

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
