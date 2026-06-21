from __future__ import annotations

import json
import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


def translate_with_openai(
    *,
    settings: Settings,
    title: str,
    source_name: str,
    source_url: str,
    raw_text: str,
    category: str | None,
    engagement_json: str | None,
) -> dict[str, str] | None:
    if not settings.openai_api_key:
        return None

    prompt = f"""
다음 원문을 한국어 뉴스레터 형식으로 정리해라.

규칙:
- 자연스러운 한국어로 쓴다.
- 원문에 없는 적용 아이디어, 성과, 구현 방식을 만들지 않는다.
- 구현 방식이 없으면 반드시 "원문에 구체적 설명 없음."이라고 쓴다.
- 영어 원문 문장을 그대로 길게 복사하지 않는다.
- JSON만 출력한다.

JSON 필드:
- title_ko: 한국어 제목
- summary_ko: 3~5문장 핵심 요약
- created_item_ko: 무엇을 만든 것인지 1~2문장
- problem_solved_ko: 어떤 문제를 해결하는지 구체적으로
- implementation_notes_ko: 원문에 나온 구현 방식만
- reaction_ko: 반응 지표 또는 반응 설명
- translation_ko: 원문 핵심 내용을 충분히 이해할 수 있는 상세 한국어 번역/요약

출처: {source_name}
URL: {source_url}
카테고리: {category or ""}
반응 지표: {engagement_json or "{}"}
제목: {title}
원문:
{raw_text[:6000]}
""".strip()

    payload = {
        "model": settings.openai_model,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "korean_case_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title_ko": {"type": "string"},
                        "summary_ko": {"type": "string"},
                        "created_item_ko": {"type": "string"},
                        "problem_solved_ko": {"type": "string"},
                        "implementation_notes_ko": {"type": "string"},
                        "reaction_ko": {"type": "string"},
                        "translation_ko": {"type": "string"},
                    },
                    "required": [
                        "title_ko",
                        "summary_ko",
                        "created_item_ko",
                        "problem_solved_ko",
                        "implementation_notes_ko",
                        "reaction_ko",
                        "translation_ko",
                    ],
                },
            }
        },
    }

    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        content = _extract_output_text(response.json())
        data = json.loads(content)
        return {key: str(value).strip() for key, value in data.items()}
    except Exception:
        logger.exception("OpenAI translation failed; falling back to local summary")
        return None


def _extract_output_text(payload: dict) -> str:
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                chunks.append(content.get("text", ""))
    return "".join(chunks).strip()
