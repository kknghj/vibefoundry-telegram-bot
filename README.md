# Telegram GPTERS Case Digest Bot

매일 아침 8시, 저녁 8시에 지피터스 사례글 1건을 텔레그램으로 보내는 Python 봇입니다.

## 발송 범위

- 소스: 지피터스 사례글
- 작성일: `2026-07-20` 이후
- 작성자: `자연어회계처리`, `유피테르`, `벤쿠버쪼`, `이생강`, `Giacomo`, `망원궁예`
- 선택: 최신순이 아니라 미발송 글 중 랜덤 1건
- 중복 발송 방지
- 미발송 글이 모두 소진되면 안내 메시지를 보내고 봇 종료

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

## 지금 1건 발송

```powershell
python scripts/run_once.py
```

## 봇 실행

```powershell
python -m app.main
```

## 주요 설정

```text
SEND_HOURS=8,20
SEND_MINUTE=0
GPTERS_AUTHORS=자연어회계처리,유피테르,벤쿠버쪼,이생강,Giacomo,망원궁예
GPTERS_PUBLISHED_AFTER=2026-07-20
TIMEZONE=Asia/Seoul
```
