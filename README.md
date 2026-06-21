# Telegram AI News Bot

매일 오전 8시 텔레그램으로 AI 활용 사례 또는 바이브코딩 사례 1건을 보내는 Python MVP입니다.

## 주요 기능

- Telegram Bot API 발송 및 `/today`, `/next`, `/sources` 명령
- APScheduler 기반 매일 오전 8시 자동 실행
- SQLite 저장소
- Reddit RSS, GeekNews RSS, 수동 큐 기본 지원
- YouTube, Product Hunt, X는 API 키가 있을 때만 활성화
- URL, 프로젝트명, 작성자+프로젝트 조합 기반 중복 방지
- 최근 14일 카테고리 균형 반영
- `OPENAI_API_KEY`가 있으면 외국어 원문을 자연스러운 한국어로 요약/번역
- 원문 근거 없는 적용 아이디어 생성을 피하는 요약 포맷

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 최소한 다음 값을 설정하세요.

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

자연스러운 한국어 번역을 사용하려면 다음 값도 설정하세요.

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

키가 없으면 로컬 fallback 요약을 사용하지만, 임의의 외국어 원문을 매끄럽게 번역하려면 API 키 설정을 권장합니다.

## DB 초기화

```powershell
python scripts/init_db.py
```

## 한 번 수집

```powershell
python scripts/collect_once.py
```

## 다음 후보 미리보기

```powershell
python scripts/preview_next.py
```

## 오늘 사례 발송

```powershell
python scripts/run_once.py
```

## 봇 실행

```powershell
python -m app.main
```

## 운영 메모

- X는 공식 API 토큰이 있을 때만 사용합니다. 우회 스크래핑은 구현하지 않았습니다.
- API 키가 없는 소스는 비활성화 상태로 기록됩니다.
- 원문에 구현 방식이 없으면 메시지에 `원문에 구체적 설명 없음`으로 표시합니다.
