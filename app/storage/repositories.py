from __future__ import annotations

from datetime import datetime, timedelta
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import RawItem
from app.curation.classifier import classify_item
from app.curation.scorer import score_candidate
from app.storage.models import Candidate, CollectionRun, SentItem, Source
from app.utils.text import canonicalize_url, detect_language, normalize_key, stable_hash
from app.utils.time import utcnow


def upsert_source(session: Session, name: str, source_type: str, enabled: bool = True, error: str | None = None) -> Source:
    source = session.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name, type=source_type, enabled=enabled)
        session.add(source)
    source.type = source_type
    source.enabled = enabled
    source.last_checked_at = utcnow()
    if error:
        source.last_error = error[:4000]
    else:
        source.last_success_at = utcnow()
        source.last_error = None
    return source


def save_collection_run(
    session: Session,
    source_name: str,
    status: str,
    started_at: datetime,
    fetched_count: int,
    saved_count: int,
    error_message: str | None = None,
) -> None:
    session.add(
        CollectionRun(
            source_name=source_name,
            status=status,
            started_at=started_at,
            finished_at=utcnow(),
            fetched_count=fetched_count,
            saved_count=saved_count,
            error_message=error_message,
        )
    )


def candidate_exists(session: Session, source_name: str, external_id: str | None) -> bool:
    if not external_id:
        return False
    return session.scalar(
        select(Candidate.id).where(Candidate.source_name == source_name, Candidate.external_id == external_id)
    ) is not None


def save_raw_item(
    session: Session,
    item: RawItem,
    recent_categories: list[str] | None = None,
    *,
    force_accept: bool = False,
) -> Candidate | None:
    existing = session.scalar(
        select(Candidate).where(Candidate.source_name == item.source_name, Candidate.external_id == item.external_id)
    )
    canonical_url = canonicalize_url(item.source_url)
    combined_text = f"{item.title}\n{item.raw_text}"
    if force_accept:
        classification = classify_item(item.title, item.raw_text, item.source_name)
        category = classification.category if not classification.reject_reason else "바이브코딩서비스"
        priority_type = classification.priority_type if not classification.reject_reason else "개인프로젝트"
        tags = classification.tags if not classification.reject_reason else ["#지피터스", "#사례글"]
        project_name = classification.project_name
        service_name = classification.service_name
        status = "new"
        reject_reason = None
    else:
        classification = classify_item(item.title, item.raw_text, item.source_name)
        category = classification.category
        priority_type = classification.priority_type
        tags = classification.tags
        project_name = classification.project_name
        service_name = classification.service_name
        status = "rejected" if classification.reject_reason else "new"
        reject_reason = classification.reject_reason

    if existing is not None:
        if existing.status == "sent":
            return None
        existing.source_url = item.source_url
        existing.canonical_url = canonical_url
        existing.title = item.title[:1000]
        existing.author = item.author
        existing.project_name = project_name
        existing.service_name = service_name or existing.service_name
        existing.raw_text = item.raw_text
        existing.language = detect_language(combined_text)
        existing.published_at = item.published_at
        existing.engagement_json = json.dumps(item.engagement, ensure_ascii=False)
        existing.category = category
        existing.priority_type = priority_type
        existing.tags_json = json.dumps(tags, ensure_ascii=False)
        if force_accept or existing.status == "rejected":
            existing.status = status
            existing.reject_reason = reject_reason
        existing.score = 50.0 if force_accept else score_candidate(existing, recent_categories or [])
        return existing

    candidate = Candidate(
        source_name=item.source_name,
        source_url=item.source_url,
        canonical_url=canonical_url,
        title=item.title[:1000],
        author=item.author,
        project_name=project_name,
        service_name=service_name,
        raw_text=item.raw_text,
        language=detect_language(combined_text),
        published_at=item.published_at,
        engagement_json=json.dumps(item.engagement, ensure_ascii=False),
        category=category,
        priority_type=priority_type,
        tags_json=json.dumps(tags, ensure_ascii=False),
        status=status,
        reject_reason=reject_reason,
        external_id=item.external_id,
    )
    candidate.score = 50.0 if force_accept else score_candidate(candidate, recent_categories or [])
    session.add(candidate)
    return candidate


def recent_sent_categories(session: Session, days: int = 14) -> list[str]:
    since = utcnow() - timedelta(days=days)
    rows = session.scalars(select(SentItem.category).where(SentItem.sent_at >= since).order_by(SentItem.sent_at.desc())).all()
    return [row for row in rows if row]


def rescore_active_candidates(session: Session, recent_categories: list[str] | None = None) -> dict[str, int]:
    recent = recent_categories or recent_sent_categories(session)
    candidates = session.scalars(
        select(Candidate).where(Candidate.status.in_(["new", "shortlisted", "selected"]))
    ).all()
    updated = 0
    for candidate in candidates:
        new_score = score_candidate(candidate, recent)
        if candidate.score != new_score:
            candidate.score = new_score
            updated += 1
    return {"total": len(candidates), "updated": updated}


def has_been_sent_today(session: Session, day_start_utc: datetime) -> SentItem | None:
    return session.scalar(select(SentItem).where(SentItem.sent_at >= day_start_utc).order_by(SentItem.sent_at.desc()))


def has_been_sent_since(session: Session, since_utc: datetime) -> SentItem | None:
    return session.scalar(select(SentItem).where(SentItem.sent_at >= since_utc).order_by(SentItem.sent_at.desc()))


def record_sent(session: Session, candidate: Candidate, message_text: str, telegram_message_id: str | None = None) -> SentItem:
    project_key = normalize_key(candidate.project_name or candidate.service_name or candidate.title)
    author_key = normalize_key(candidate.author)
    sent = SentItem(
        candidate_id=candidate.id,
        message_text=message_text,
        url_hash=stable_hash(candidate.canonical_url),
        project_key=project_key,
        author_project_key=f"{author_key}:{project_key}" if author_key and project_key else None,
        category=candidate.category,
        telegram_message_id=telegram_message_id,
    )
    candidate.status = "sent"
    session.add(sent)
    return sent
