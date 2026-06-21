from app.curation.scorer import least_recent_category


def test_least_recent_category_prefers_missing_category():
    assert least_recent_category(["업무자동화", "바이브코딩서비스"]) == "재미있는프로젝트"


def test_least_recent_category_when_all_seen():
    recent = ["업무자동화", "바이브코딩서비스", "재미있는프로젝트", "수익화사례", "공공기관응용"]
    assert least_recent_category(recent) == "공공기관응용"
