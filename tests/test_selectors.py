from app.curation.selector import select_next_candidate
from app.storage.models import Candidate


def test_selector_picks_highest_non_duplicate(session):
    low = Candidate(
        source_name="manual",
        source_url="https://example.com/low",
        canonical_url="https://example.com/low",
        title="Low",
        score=10,
        status="new",
    )
    high = Candidate(
        source_name="manual",
        source_url="https://example.com/high",
        canonical_url="https://example.com/high",
        title="High",
        score=90,
        status="new",
    )
    session.add_all([low, high])
    session.commit()
    assert select_next_candidate(session).title == "High"
