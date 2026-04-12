---
paths:
  - src/quota/**
  - src/cache/**
---

### 쿼터/캐시 시스템

- **`src/quota/gemini_quota.py`**: RPM 50 제한, 이미지 일 500장, 일간 자동 리셋. 상태 파일 `data/global/quota/gemini_quota_daily.json`.
- **`src/quota/youtube_quota.py`**: 일 10,000단위, 업로드 1건=1,700단위. 부족 시 `deferred_jobs`에 이연 → 다음 실행 시 자동 재시도.
- **`src/quota/ytdlp_quota.py`**: RPM 30, User-Agent 로테이션, 차단 감지 시 5분 대기.
- **`src/cache/gemini_cache.py`**: diskcache 기반, TTL 24h, 500MB. 특정 프롬프트 타입만 캐싱.

**주의**: `src/quota/__init__.py`는 23KB 레거시 파일로, yt-dlp 채널 수집 로직이 포함되어 있다. 일반적인 패키지 init이 아님.
