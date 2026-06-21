from __future__ import annotations

from datetime import datetime, timezone
import json

from app.storage.models import Candidate
from app.utils.time import utcnow

PRIORITY_POINTS = {
    "공개서비스": 30,
    "업무자동화": 24,
    "개인프로젝트": 18,
    "수익화사례": 15,
    "기술소개": 5,
}

TARGET_ROTATION = ["업무자동화", "바이브코딩서비스", "재미있는프로젝트", "수익화사례", "공공기관응용"]


def score_candidate(candidate: Candidate, recent_categories: list[str]) -> float:
    if candidate.reject_reason or candidate.priority_type == "excluded":
        return -100.0
    score = 0.0
    score += PRIORITY_POINTS.get(candidate.priority_type or "", 0)
    text = f"{candidate.title}\n{candidate.raw_text or ''}".lower()
    if any(k in text for k in ["built", "launched", "created", "만들", "개발", "출시", "demo"]):
        score += 20
    if any(k in text for k in ["problem", "save time", "workflow", "manual", "반복", "문제", "시간"]):
        score += 15
    if len(candidate.raw_text or "") > 140:
        score += 10
    score += min(_engagement_points(candidate.engagement_json), 15)
    score += _freshness_points(candidate.published_at)
    score += category_balance_adjustment(candidate.category, recent_categories)
    return round(max(min(score, 100), -100), 2)


def category_balance_adjustment(category: str | None, recent_categories: list[str]) -> float:
    if not category:
        return 0
    adjustment = 0.0
    counts = {name: recent_categories.count(name) for name in TARGET_ROTATION}
    if counts.get(category, 0) >= 3:
        adjustment -= 10
    if len(recent_categories) >= 3 and all(item == category for item in recent_categories[:3]):
        adjustment -= 15
    if category == least_recent_category(recent_categories):
        adjustment += 10
    return adjustment


def least_recent_category(recent_categories: list[str]) -> str:
    for category in TARGET_ROTATION:
        if category not in recent_categories:
            return category
    positions = {category: recent_categories.index(category) for category in TARGET_ROTATION}
    return max(positions, key=positions.get)


def _engagement_points(raw: str | None) -> float:
    if not raw:
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    total = 0
    for key in ["votes", "likes", "like_count", "ups", "score"]:
        value = data.get(key)
        if isinstance(value, int | float):
            total += value
    comments = data.get("comments") or data.get("comment_count") or data.get("num_comments")
    if isinstance(comments, int | float):
        total += comments * 2
    if total <= 0:
        return 0
    if total >= 500:
        return 15
    if total >= 100:
        return 10
    if total >= 20:
        return 6
    return 3


def _freshness_points(published_at: datetime | None) -> float:
    if published_at is None:
        return 3
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_days = (utcnow() - published_at).days
    if age_days <= 2:
        return 10
    if age_days <= 7:
        return 7
    if age_days <= 30:
        return 4
    return 1
