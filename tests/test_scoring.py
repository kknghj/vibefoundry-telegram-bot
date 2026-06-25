import json
from datetime import timedelta

from app.curation.scorer import (
    category_balance_adjustment,
    score_candidate,
    _engagement_points,
    _engagement_total,
)
from app.storage.models import Candidate
from app.utils.time import utcnow


def test_public_service_scores_above_technical_intro():
    public = Candidate(
        source_name="product_hunt",
        source_url="https://example.com/a",
        canonical_url="https://example.com/a",
        title="I built an AI automation app",
        priority_type="공개서비스",
        category="바이브코딩서비스",
        raw_text="Built a demo to save time in manual workflow",
        published_at=utcnow(),
    )
    tech = Candidate(
        source_name="geeknews",
        source_url="https://example.com/b",
        canonical_url="https://example.com/b",
        title="AI model benchmark notes",
        priority_type="기술소개",
        category="기술소개",
        raw_text="benchmark comparison",
        published_at=utcnow() - timedelta(days=20),
    )
    assert score_candidate(public, []) > score_candidate(tech, [])


def test_repeated_category_gets_penalty():
    recent = ["업무자동화", "업무자동화", "업무자동화", "수익화사례"]
    assert category_balance_adjustment("업무자동화", recent) < 0


def test_high_engagement_scores_above_low_engagement():
    base = {
        "source_name": "product_hunt",
        "source_url": "https://example.com/item",
        "canonical_url": "https://example.com/item",
        "title": "I built an AI automation app",
        "priority_type": "개인프로젝트",
        "category": "바이브코딩서비스",
        "raw_text": "Built a demo to save time in manual workflow",
        "published_at": utcnow(),
    }
    low = Candidate(**base, engagement_json=json.dumps({"votes": 3, "comments": 1}))
    high = Candidate(**base, engagement_json=json.dumps({"votes": 800, "comments": 120}))
    assert score_candidate(high, []) > score_candidate(low, [])


def test_engagement_uses_log_scale_and_x_metrics():
    low = _engagement_points(json.dumps({"like_count": 5, "reply_count": 1}))
    high = _engagement_points(json.dumps({"like_count": 500, "reply_count": 80, "retweet_count": 40}))
    assert high > low
    assert _engagement_total({"ups": 100, "score": 95, "num_comments": 10}) == 120
