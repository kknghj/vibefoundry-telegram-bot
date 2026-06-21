from app.bot.message_formatter import format_candidate_message
from app.storage.models import Candidate


def test_message_escapes_html():
    candidate = Candidate(
        source_name="reddit_test",
        source_url="https://example.com/?a=1&b=2",
        canonical_url="https://example.com",
        title="AI <Inbox> & Sorter",
        project_name="AI Inbox Sorter",
        summary_ko="A < B & C",
        problem_solved_ko="반복 업무 해결",
        implementation_notes_ko="원문에 구체적 설명 없음.",
        reaction_ko="댓글 있음",
        translation_ko="번역",
        tags_json='["#업무자동화", "#바이브코딩"]',
    )
    message = format_candidate_message(candidate)
    assert "&lt;Inbox&gt;" in message
    assert "a=1&amp;b=2" in message
