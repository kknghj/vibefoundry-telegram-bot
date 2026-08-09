from datetime import datetime, timezone

from app.curation.selector import select_random_gpters_candidate
from app.storage.models import Candidate


def test_selector_picks_eligible_gpters_author_randomly(session):
    cutoff = datetime(2026, 7, 20, tzinfo=timezone.utc)
    eligible = Candidate(
        source_name="gpters",
        source_url="https://www.gpters.org/nocode/post/eligible",
        canonical_url="https://www.gpters.org/nocode/post/eligible",
        title="Eligible",
        author="유피테르",
        published_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        score=10,
        status="new",
    )
    too_old = Candidate(
        source_name="gpters",
        source_url="https://www.gpters.org/nocode/post/old",
        canonical_url="https://www.gpters.org/nocode/post/old",
        title="Old",
        author="유피테르",
        published_at=datetime(2026, 7, 19, tzinfo=timezone.utc),
        score=90,
        status="new",
    )
    other_author = Candidate(
        source_name="gpters",
        source_url="https://www.gpters.org/nocode/post/other",
        canonical_url="https://www.gpters.org/nocode/post/other",
        title="Other",
        author="다른사람",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        score=90,
        status="new",
    )
    session.add_all([eligible, too_old, other_author])
    session.commit()

    selected = select_random_gpters_candidate(
        session,
        authors=["유피테르"],
        published_after=cutoff,
    )
    assert selected is not None
    assert selected.title == "Eligible"
