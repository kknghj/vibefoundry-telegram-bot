from app.curation.summarizer import enrich_candidate
from app.storage.models import Candidate


def test_english_subscription_case_gets_korean_fallback():
    candidate = Candidate(
        source_name="reddit_sideproject",
        source_url="https://reddit.com/example",
        canonical_url="https://reddit.com/example",
        title="I built a subscription tracker because my wife and I kept paying for the same things twice",
        raw_text=(
            "A few months ago my wife and I actually sat down and added up our subscriptions. "
            "Two Spotify accounts, two overlapping iCloud storage tiers, and a YouTube Premium Family plan."
        ),
        language="en",
    )

    enrich_candidate(candidate, force=True)

    assert "구독 추적" in candidate.summary_ko
    assert "작성자는 몇 달 전" in candidate.translation_ko
    assert "A few months ago" not in candidate.translation_ko
