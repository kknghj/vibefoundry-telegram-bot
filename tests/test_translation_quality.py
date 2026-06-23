from app.curation.summarizer import is_delivery_ready, needs_translation_refresh
from app.storage.models import Candidate


def test_legacy_mixed_english_summary_needs_refresh():
    candidate = Candidate(
        source_name="reddit_sideproject",
        source_url="https://reddit.com/example",
        canonical_url="https://reddit.com/example",
        title="I built a visual batch media optimizer",
        language="en",
        summary_ko="원문은 'I built a visual batch media optimizer' 사례를 소개한다. 핵심 내용은 다음과 같다: Hey everyone.",
        problem_solved_ko="반복적인 파일 처리 문제를 다룬다.",
        translation_ko="외국어 원문 핵심 내용 요약: Hey everyone. I built this tool.",
    )

    assert needs_translation_refresh(candidate)
    assert not is_delivery_ready(candidate)


def test_korean_translation_is_delivery_ready():
    candidate = Candidate(
        source_name="reddit_sideproject",
        source_url="https://reddit.com/example",
        canonical_url="https://reddit.com/example",
        title="I built a visual batch media optimizer",
        language="en",
        service_name="저사양 PC를 위한 미디어 일괄 최적화 도구",
        summary_ko="작성자는 저사양 PC에서 영상 편집 프로그램을 돌리기 어려워 미디어 파일을 한 번에 최적화하는 도구를 만들었다.",
        problem_solved_ko="이미지, 오디오, 영상 파일을 대량으로 줄이는 문제를 다룬다.",
        translation_ko="작성자는 저사양 PC에서 작업하던 개인적인 불편에서 이 프로젝트를 시작했다고 설명한다.",
    )

    assert not needs_translation_refresh(candidate)
    assert is_delivery_ready(candidate)
