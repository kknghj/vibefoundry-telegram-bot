from __future__ import annotations

from app.storage.models import Candidate
from app.utils.text import compact_whitespace


def enrich_candidate(candidate: Candidate) -> Candidate:
    text = compact_whitespace(candidate.raw_text or "")
    title = candidate.title.strip()
    if not candidate.summary_ko:
        candidate.summary_ko = _summary(title, text)
    if not candidate.problem_solved_ko:
        candidate.problem_solved_ko = _problem(candidate.category)
    if not candidate.implementation_notes_ko:
        candidate.implementation_notes_ko = _implementation(text)
    if not candidate.reaction_ko:
        candidate.reaction_ko = _reaction(candidate.source_name, candidate.engagement_json)
    if not candidate.translation_ko:
        candidate.translation_ko = _translation(candidate.language, text)
    return candidate


def _summary(title: str, text: str) -> str:
    if text:
        clipped = text[:500]
        return f"원문은 '{title}' 사례를 소개한다. 핵심 내용은 다음과 같다: {clipped}"
    return f"원문은 '{title}' 사례를 소개하지만, 수집된 본문 설명은 길지 않다. 제목과 출처 정보를 기준으로 실제 제작 또는 공개 사례 여부를 확인한 후보이다."


def _problem(category: str | None) -> str:
    if category == "업무자동화":
        return "반복적인 업무 처리나 수작업 흐름을 줄이는 문제를 다룬다. 구체 범위는 원문에 공개된 설명 안에서만 판단했다."
    if category == "수익화사례":
        return "개인 또는 소규모 팀이 만든 프로젝트를 사용자 확보나 매출로 연결하는 문제를 다룬다."
    if category == "공공기관응용":
        return "행정, 민원, 공공 서비스처럼 반복적이고 문서 중심인 업무에 연결될 수 있는 사례다."
    return "사용자가 직접 만든 앱, 서비스 또는 개인 프로젝트를 통해 특정 불편을 해결하려는 사례다."


def _implementation(text: str) -> str:
    lowered = text.lower()
    hints = []
    for key in ["cursor", "claude", "chatgpt", "openai", "python", "react", "api", "zapier", "make.com"]:
        if key in lowered:
            hints.append(key)
    if hints:
        return "원문에서 확인되는 구현 단서: " + ", ".join(dict.fromkeys(hints)) + ". 원문에 없는 세부 구조는 추가로 추정하지 않았다."
    return "원문에 구체적 설명 없음."


def _reaction(source_name: str, engagement_json: str | None) -> str:
    if engagement_json and engagement_json != "{}":
        return f"수집된 반응 지표: {engagement_json}"
    return f"{source_name}에서 수집했으며, MVP 수집 범위에서는 별도 반응 지표를 확인하지 못했다."


def _translation(language: str | None, text: str) -> str:
    if language == "ko":
        return "원문이 한국어이므로 별도 번역 없이 핵심 내용을 정리했다."
    if text:
        return "외국어 원문 핵심 내용 요약: " + text[:800]
    return "외국어 원문이거나 본문이 짧아, 제목과 출처 중심으로만 이해 가능한 범위를 정리했다."
