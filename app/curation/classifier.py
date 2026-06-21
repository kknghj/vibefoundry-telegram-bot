from __future__ import annotations

from dataclasses import dataclass
import re

from app.utils.text import compact_whitespace

CATEGORIES = ["업무자동화", "바이브코딩서비스", "재미있는프로젝트", "수익화사례", "공공기관응용"]

EXCLUDE_PATTERNS = [
    (r"\b(funding|raises|raised|investment|investor|series [abc])\b", "투자 뉴스"),
    (r"\b(benchmark|leaderboard|model comparison|beats gpt|outperforms)\b", "모델 성능 비교"),
    (r"\b(paper|arxiv|researchers propose)\b", "논문 소개"),
    (r"(논문|연구자|연구의|머신러닝 연구|기술 동향|모델 성능|벤치마크)", "기술/연구 소개"),
]


@dataclass(frozen=True)
class Classification:
    category: str
    priority_type: str
    tags: list[str]
    project_name: str | None
    service_name: str | None
    reject_reason: str | None = None


def classify_item(title: str, raw_text: str, source_name: str) -> Classification:
    text = compact_whitespace(f"{title} {raw_text}")
    lowered = text.lower()
    for pattern, reason in EXCLUDE_PATTERNS:
        if re.search(pattern, lowered):
            return Classification("기술소개", "excluded", ["#제외"], _project_name(title), None, reason)

    has_built_signal = any(
        key in lowered
        for key in ["built", "launched", "made", "created", "i built", "we built", "cursor", "claude code", "vibe coding", "만들", "개발", "출시"]
    )
    has_automation = any(key in lowered for key in ["automation", "automate", "workflow", "zapier", "업무", "자동화", "반복"])
    has_revenue = any(key in lowered for key in ["mrr", "revenue", "customers", "paid", "sales", "수익", "매출", "유료"])
    has_public = any(
        key in lowered
        for key in [
            "product hunt",
            "launched",
            "app",
            "service",
            "website",
            "chrome extension",
            "subscription tracker",
            "서비스",
            "앱",
            "웹앱",
            "확장",
        ]
    )
    has_civic = any(key in lowered for key in ["government", "public sector", "municipal", "admin", "공공", "행정", "민원"])
    has_case_signal = any(
        key in lowered
        for key in [
            "i built",
            "we built",
            "i made",
            "we made",
            "launched",
            "my app",
            "our app",
            "case study",
            "built a",
            "built an",
            "만들었습니다",
            "개발했습니다",
            "출시했습니다",
        ]
    )

    if not has_built_signal and source_name not in {"product_hunt", "manual_queue"}:
        return Classification("기술소개", "excluded", ["#제외"], _project_name(title), None, "구현 결과물 신호 부족")
    if source_name == "geeknews" and not (has_case_signal or has_public or has_automation or has_revenue or has_civic):
        return Classification("기술소개", "excluded", ["#제외"], _project_name(title), None, "실제 사례 신호 부족")

    if has_civic:
        category = "공공기관응용"
        tags = ["#공공기관응용", "#AI활용"]
    elif has_automation:
        category = "업무자동화"
        tags = ["#업무자동화", "#AI활용"]
    elif has_revenue:
        category = "수익화사례"
        tags = ["#수익화", "#사이드프로젝트"]
    elif "vibe" in lowered or "cursor" in lowered or "claude code" in lowered:
        category = "바이브코딩서비스"
        tags = ["#바이브코딩", "#서비스"]
    else:
        category = "재미있는프로젝트"
        tags = ["#사이드프로젝트", "#개인프로젝트"]

    if has_public:
        priority = "공개서비스"
    elif has_automation:
        priority = "업무자동화"
    elif has_revenue:
        priority = "수익화사례"
    else:
        priority = "개인프로젝트"

    project_name = _project_name(title)
    return Classification(category, priority, tags, project_name, project_name if has_public else None)


def _project_name(title: str) -> str | None:
    cleaned = compact_whitespace(title)
    cleaned = re.sub(r"^(show hn:|show reddit:|launch:)", "", cleaned, flags=re.IGNORECASE).strip()
    if not cleaned:
        return None
    return cleaned[:120]
