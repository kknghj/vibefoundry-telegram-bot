from app.curation.deduplicator import is_duplicate_sent
from app.storage.models import Candidate
from app.storage.repositories import record_sent


def test_duplicate_by_url(session):
    sent_candidate = Candidate(
        source_name="manual",
        source_url="https://example.com/app?utm_source=x",
        canonical_url="https://example.com/app",
        title="Example App",
        project_name="Example App",
        category="바이브코딩서비스",
    )
    session.add(sent_candidate)
    session.commit()
    record_sent(session, sent_candidate, "message")
    session.commit()
    candidate = Candidate(
        source_name="manual",
        source_url="https://example.com/app?ref=y",
        canonical_url="https://example.com/app",
        title="Other title",
        project_name="Other title",
    )
    assert is_duplicate_sent(session, candidate)


def test_duplicate_by_project_name(session):
    sent_candidate = Candidate(
        source_name="manual",
        source_url="https://example.com/a",
        canonical_url="https://example.com/a",
        title="AI Inbox Sorter",
        project_name="AI Inbox Sorter",
        category="업무자동화",
    )
    session.add(sent_candidate)
    session.commit()
    record_sent(session, sent_candidate, "message")
    session.commit()
    candidate = Candidate(
        source_name="manual",
        source_url="https://another.example.com",
        canonical_url="https://another.example.com",
        title="AI Inbox Sorter launch update",
        project_name="AI Inbox Sorter",
    )
    assert is_duplicate_sent(session, candidate)
