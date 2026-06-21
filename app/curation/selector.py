from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.curation.deduplicator import is_duplicate_sent
from app.storage.models import Candidate


def select_next_candidate(session: Session) -> Candidate | None:
    candidates = session.scalars(
        select(Candidate)
        .where(Candidate.status.in_(["new", "shortlisted", "selected"]))
        .where(Candidate.score > 0)
        .order_by(Candidate.score.desc(), Candidate.collected_at.desc())
        .limit(100)
    ).all()
    for candidate in candidates:
        if is_duplicate_sent(session, candidate):
            candidate.status = "rejected"
            candidate.reject_reason = "이미 발송한 URL 또는 프로젝트"
            continue
        candidate.status = "selected"
        return candidate
    return None
