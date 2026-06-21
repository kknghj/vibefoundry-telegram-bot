from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import Candidate, SentItem
from app.utils.text import normalize_key, stable_hash


def is_duplicate_sent(session: Session, candidate: Candidate) -> bool:
    url_hash = stable_hash(candidate.canonical_url)
    if session.scalar(select(SentItem.id).where(SentItem.url_hash == url_hash)) is not None:
        return True
    project_key = normalize_key(candidate.project_name or candidate.service_name or candidate.title)
    if project_key and session.scalar(select(SentItem.id).where(SentItem.project_key == project_key)) is not None:
        return True
    author_key = normalize_key(candidate.author)
    if author_key and project_key:
        author_project_key = f"{author_key}:{project_key}"
        if session.scalar(select(SentItem.id).where(SentItem.author_project_key == author_project_key)) is not None:
            return True
    return False
