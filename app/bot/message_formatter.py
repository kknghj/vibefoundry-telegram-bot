from __future__ import annotations

from html import escape
import json

from app.storage.models import Candidate

TELEGRAM_LIMIT = 4096
SAFE_LIMIT = 3800


def format_candidate_message(candidate: Candidate, preview: bool = False) -> str:
    tags = _tags(candidate.tags_json)
    prefix = "🔎 다음 후보 미리보기" if preview else "📬 지피터스 사례글"
    source = candidate.source_name.replace("_", " / ")
    author = candidate.author or "작성자 미상"
    parts = [
        f"<b>{escape(prefix)}</b>",
        "",
        "<b>제목:</b>",
        escape(_display_title(candidate)),
        "",
        "<b>작성자:</b>",
        escape(author),
        "",
        "<b>출처:</b>",
        escape(source),
        "",
        "<b>원문:</b>",
        escape(candidate.source_url),
        "",
        "<b>핵심 요약:</b>",
        escape(candidate.summary_ko or "요약 전 후보입니다."),
        "",
        "<b>무엇을 만든 것인가?</b>",
        escape(candidate.service_name or candidate.project_name or candidate.title),
        "",
        "<b>어떤 문제를 해결하는가?</b>",
        escape(candidate.problem_solved_ko or "원문에 구체적 설명 없음."),
        "",
        "<b>어떻게 구현했는가?</b>",
        escape(candidate.implementation_notes_ko or "원문에 구체적 설명 없음."),
        "",
        "<b>반응:</b>",
        escape(candidate.reaction_ko or "확인된 반응 지표 없음."),
        "",
        "<b>상세 번역:</b>",
        escape(candidate.translation_ko or "원문 정보가 짧아 별도 상세 번역 없음."),
        "",
        "<b>태그:</b>",
        escape(" ".join(tags)),
    ]
    message = "\n".join(parts)
    if len(message) <= SAFE_LIMIT:
        return message
    short_parts = parts[:29] + [
        "",
        "<b>상세 번역:</b>",
        escape(_clip(candidate.translation_ko, 700) or "길이 제한으로 상세 번역을 압축했다."),
        "",
        "<b>태그:</b>",
        escape(" ".join(tags)),
    ]
    return "\n".join(short_parts)[:TELEGRAM_LIMIT]


def _tags(raw: str | None) -> list[str]:
    if not raw:
        return ["#지피터스", "#사례글"]
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) and parsed else ["#지피터스", "#사례글"]
    except json.JSONDecodeError:
        return ["#지피터스", "#사례글"]


def _clip(value: str | None, limit: int) -> str:
    if not value or len(value) <= limit:
        return value or ""
    return value[: limit - 20].rstrip() + "..."


def _display_title(candidate: Candidate) -> str:
    if candidate.language != "ko" and candidate.service_name:
        return candidate.service_name
    return candidate.title
