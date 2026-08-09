from __future__ import annotations

from datetime import datetime, timezone
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.curation.deduplicator import is_duplicate_sent
from app.storage.models import Candidate


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def select_next_candidate(session: Session) -> Candidate | None:
    selected = select_diverse_candidates(session, count=1)
    return selected[0] if selected else None


def select_diverse_candidates(
    session: Session,
    count: int,
    *,
    exclude_ids: set[int] | None = None,
    used_sources: set[str] | None = None,
    used_categories: set[str] | None = None,
) -> list[Candidate]:
    del used_sources, used_categories
    return select_random_candidates(session, count, exclude_ids=exclude_ids or set())


def select_random_gpters_candidate(
    session: Session,
    *,
    authors: tuple[str, ...] | list[str],
    published_after: datetime,
    exclude_ids: set[int] | None = None,
) -> Candidate | None:
    selected = select_random_candidates(
        session,
        1,
        exclude_ids=exclude_ids or set(),
        authors=authors,
        published_after=published_after,
        source_name="gpters",
    )
    return selected[0] if selected else None


def select_random_candidates(
    session: Session,
    count: int,
    *,
    exclude_ids: set[int] | None = None,
    authors: tuple[str, ...] | list[str] | None = None,
    published_after: datetime | None = None,
    source_name: str | None = None,
) -> list[Candidate]:
    if count <= 0:
        return []

    query = select(Candidate).where(Candidate.status.in_(["new", "shortlisted", "selected"]))
    if source_name:
        query = query.where(Candidate.source_name == source_name)
    if authors:
        query = query.where(Candidate.author.in_(list(authors)))
    candidates = list(session.scalars(query.limit(500)).all())
    if published_after is not None:
        cutoff = _as_utc(published_after)
        candidates = [
            candidate
            for candidate in candidates
            if candidate.published_at is not None and _as_utc(candidate.published_at) >= cutoff
        ]
    random.shuffle(candidates)

    selected: list[Candidate] = []
    excluded = exclude_ids or set()
    for candidate in candidates:
        if len(selected) >= count:
            break
        if candidate.id in excluded:
            continue
        if is_duplicate_sent(session, candidate):
            candidate.status = "rejected"
            candidate.reject_reason = "이미 발송한 URL 또는 프로젝트"
            continue
        candidate.status = "selected"
        selected.append(candidate)
    return selected
