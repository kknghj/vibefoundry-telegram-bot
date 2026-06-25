import asyncio
import json

from _bootstrap import setup_script

setup_script()

from sqlalchemy import select

from app.collectors.reddit import fetch_post_engagement
from app.config import get_settings
from app.storage.db import create_session_factory
from app.storage.models import Candidate
from app.storage.repositories import rescore_active_candidates


ACTIVE_STATUSES = ("new", "shortlisted", "selected")


async def main() -> None:
    settings = get_settings()
    factory = create_session_factory(settings)
    with factory() as session:
        active = session.scalars(select(Candidate).where(Candidate.status.in_(ACTIVE_STATUSES))).all()

        reddit_missing = [
            candidate
            for candidate in active
            if candidate.source_name.startswith("reddit_")
            and (not candidate.engagement_json or candidate.engagement_json == "{}")
            and candidate.external_id
        ]
        if reddit_missing:
            engagement_map = await fetch_post_engagement([c.external_id for c in reddit_missing])
            refreshed = 0
            for candidate in reddit_missing:
                data = engagement_map.get(candidate.external_id)
                if not data and candidate.external_id.startswith("t3_"):
                    data = engagement_map.get(candidate.external_id.removeprefix("t3_"))
                if data:
                    candidate.engagement_json = json.dumps(data, ensure_ascii=False)
                    refreshed += 1
            if refreshed:
                print(f"Reddit engagement refreshed: {refreshed}/{len(reddit_missing)}")
            else:
                print(
                    f"Reddit engagement refresh skipped or failed for {len(reddit_missing)} posts "
                    "(existing scores will still be updated)"
                )

        result = rescore_active_candidates(session)
        session.commit()
        print(f"Rescored candidates: {result['updated']}/{result['total']}")

        top = session.scalars(
            select(Candidate)
            .where(Candidate.status.in_(ACTIVE_STATUSES))
            .where(Candidate.score > 0)
            .order_by(Candidate.score.desc(), Candidate.collected_at.desc())
            .limit(5)
        ).all()
        if top:
            print("Top candidates after rescore:")
            for candidate in top:
                print(f"  score={candidate.score} | {candidate.title[:70]} | {candidate.engagement_json}")


if __name__ == "__main__":
    asyncio.run(main())
