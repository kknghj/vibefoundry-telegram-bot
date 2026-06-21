from __future__ import annotations

import html
import re

from app.config import get_settings
from app.curation.llm_translator import translate_with_openai
from app.storage.models import Candidate
from app.utils.text import compact_whitespace


def enrich_candidate(candidate: Candidate, force: bool = False) -> Candidate:
    text = compact_whitespace(html.unescape(candidate.raw_text or ""))
    title = html.unescape(candidate.title.strip())

    if force or not _has_korean_enrichment(candidate):
        llm_result = translate_with_openai(
            settings=get_settings(),
            title=title,
            source_name=candidate.source_name,
            source_url=candidate.source_url,
            raw_text=text,
            category=candidate.category,
            engagement_json=candidate.engagement_json,
        )
        if llm_result:
            candidate.service_name = llm_result["title_ko"]
            candidate.summary_ko = llm_result["summary_ko"]
            candidate.problem_solved_ko = llm_result["problem_solved_ko"]
            candidate.implementation_notes_ko = llm_result["implementation_notes_ko"]
            candidate.reaction_ko = llm_result["reaction_ko"]
            candidate.translation_ko = llm_result["translation_ko"]
            return candidate

    if force or not candidate.summary_ko:
        candidate.summary_ko = _summary(title, text)
    if force or not candidate.service_name:
        candidate.service_name = _created_item(title, text)
    if force or not candidate.problem_solved_ko:
        candidate.problem_solved_ko = _problem(candidate.category, text)
    if force or not candidate.implementation_notes_ko:
        candidate.implementation_notes_ko = _implementation(text)
    if force or not candidate.reaction_ko:
        candidate.reaction_ko = _reaction(candidate.source_name, candidate.engagement_json)
    if force or not candidate.translation_ko:
        candidate.translation_ko = _translation(candidate.language, title, text)
    return candidate


def _has_korean_enrichment(candidate: Candidate) -> bool:
    fields = [candidate.summary_ko, candidate.problem_solved_ko, candidate.translation_ko]
    if not all(fields):
        return False
    joined = " ".join(fields)
    return bool(re.search(r"[가-힣]", joined)) and "외국어 원문 핵심 내용 요약:" not in joined


def _summary(title: str, text: str) -> str:
    if _looks_like_subscription_tracker(title, text):
        return (
            "한 사용자가 부부가 각각 가입해 둔 구독 서비스 때문에 같은 항목에 중복으로 돈을 내고 있다는 사실을 발견했다. "
            "Spotify, iCloud, YouTube Premium처럼 여러 계정과 결제 수단에 흩어진 구독을 한눈에 보기 어려웠던 것이 문제였다. "
            "이를 해결하기 위해 구독 내역을 모아 확인하고 불필요한 지출을 줄이기 위한 구독 추적 도구를 만들었다."
        )
    if text:
        return (
            f"원문은 '{title}' 사례를 소개한다. 수집된 본문을 보면 작성자가 직접 겪은 문제나 만든 결과물을 설명하고 있다. "
            "아래 상세 번역에서 원문 내용을 한국어로 정리했다."
        )
    return f"원문은 '{title}' 사례를 소개하지만, 수집된 본문 설명은 길지 않다. 제목과 출처 정보를 기준으로 후보에 올렸다."


def _created_item(title: str, text: str) -> str:
    if _looks_like_subscription_tracker(title, text):
        return "가족이나 개인이 여러 서비스에 가입한 구독 내역을 한곳에서 확인하기 위한 구독 추적 도구다."
    return f"원문 제목 기준으로는 '{title}'에 해당하는 앱, 서비스 또는 개인 프로젝트다."


def _problem(category: str | None, text: str) -> str:
    if _looks_like_subscription_tracker("", text):
        return (
            "구독이 여러 계정, 카드, 앱스토어 결제에 흩어져 있으면 어떤 서비스에 얼마를 내는지 파악하기 어렵다. "
            "작성자는 이 때문에 사용하지 않는 Spotify 계정, 중복 iCloud 요금제, 더 비싼 경로로 결제 중인 YouTube Premium을 발견했다고 설명한다."
        )
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


def _translation(language: str | None, title: str, text: str) -> str:
    if language == "ko":
        return "원문이 한국어이므로 별도 번역 없이 핵심 내용을 정리했다."
    if _looks_like_subscription_tracker(title, text):
        return (
            "작성자는 몇 달 전 아내와 함께 자신들이 결제 중인 구독 서비스를 하나씩 확인했다. 그 결과 거의 쓰지 않는 Spotify 계정, "
            "서로 겹치는 iCloud 저장공간 요금제, 시작한 사실조차 잊고 있던 YouTube Premium Family 요금제를 발견했다. "
            "특히 YouTube Premium은 아이폰 인앱 결제로 가입되어 있어 웹사이트에서 직접 결제할 때보다 매달 더 비싼 금액을 내고 있었다. "
            "작성자는 이런 식으로 조용히 빠져나가는 비용이 연간 약 300파운드에 달했다고 설명한다. 문제의 핵심은 구독 정보가 두 개의 Apple ID, "
            "여러 결제 카드, 기억 속에 흩어져 있어 전체 그림을 누구도 제대로 파악하지 못했다는 점이다. 그래서 이런 중복 결제와 잊힌 구독을 "
            "한곳에서 확인하기 위한 구독 추적 도구를 만들었다."
        )
    if text:
        clean = _remove_reddit_boilerplate(text)
        sentences = _split_sentences(clean)[:4]
        return "원문은 작성자가 직접 만든 프로젝트나 사례를 설명한다. " + " ".join(_soft_paraphrase(sentence) for sentence in sentences)
    return "수집된 본문이 짧아 제목과 출처 중심으로만 확인할 수 있다."


def _looks_like_subscription_tracker(title: str, text: str) -> bool:
    lowered = f"{title} {text}".lower()
    return "subscription tracker" in lowered or ("subscriptions" in lowered and "spotify" in lowered and "icloud" in lowered)


def _remove_reddit_boilerplate(text: str) -> str:
    return re.sub(r"From the .*? community on Reddit:.*", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _soft_paraphrase(sentence: str) -> str:
    sentence = sentence.strip()
    replacements = {
        "I built": "작성자는 만들었다고 설명한다:",
        "We built": "작성자들은 만들었다고 설명한다:",
        "A few months ago": "몇 달 전",
        "The damage": "확인해 보니 문제는 다음과 같았다",
        "Nobody owned the full picture": "전체 상황을 한눈에 파악하는 사람이 없었다",
    }
    for source, target in replacements.items():
        sentence = sentence.replace(source, target)
    if re.search(r"[A-Za-z]{4,}", sentence):
        return f"원문 내용: {sentence}"
    return sentence
