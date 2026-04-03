"""KAS OAuth 토큰 생성 스크립트.

사전 준비:
  1. Google Cloud Console에서 OAuth 클라이언트 ID(데스크톱 앱) 생성
  2. JSON 다운로드 후 credentials/client_secret.json 으로 저장

실행:
  python scripts/generate_oauth_token.py --channel CH1
  python scripts/generate_oauth_token.py --channel CH2
  ... 채널별로 반복

결과:
  credentials/CH1_token.json, CH2_token.json ... 생성됨
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("오류: google-auth-oauthlib 패키지가 없습니다.")
    print("설치 명령어: pip install google-auth-oauthlib")
    sys.exit(1)

# 업로드 + KPI 수집에 필요한 전체 Scope
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

CREDENTIALS_DIR = ROOT / "credentials"
CLIENT_SECRET = CREDENTIALS_DIR / "client_secret.json"

VALID_CHANNELS = [f"CH{i}" for i in range(1, 8)]


def generate_token(channel_key: str) -> None:
    """지정된 채널의 OAuth token.json을 생성한다."""
    if channel_key not in VALID_CHANNELS:
        print(f"오류: 유효하지 않은 채널 키 '{channel_key}'. 가능한 값: {VALID_CHANNELS}")
        sys.exit(1)

    if not CLIENT_SECRET.exists():
        print(f"오류: {CLIENT_SECRET} 파일이 없습니다.")
        print("Google Cloud Console에서 OAuth 클라이언트 ID JSON을 다운로드하여")
        print(f"  {CLIENT_SECRET}  경로에 저장하세요.")
        sys.exit(1)

    token_path = CREDENTIALS_DIR / f"{channel_key}_token.json"

    print(f"\n[{channel_key}] OAuth 인증을 시작합니다...")
    print("브라우저가 자동으로 열립니다.")
    print(f"중요: 인증 화면에서 '{channel_key}'에 해당하는 YouTube 채널(브랜드 계정)을 선택하세요!\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET), SCOPES
    )
    # 로컬 서버로 인증 코드를 수신 (포트 0 = OS가 자동 선택)
    creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n토큰 저장 완료: {token_path}")
    print("이 파일은 자동으로 갱신되므로 한 번만 생성하면 됩니다.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="KAS YouTube 채널 OAuth 토큰 생성"
    )
    parser.add_argument(
        "--channel",
        required=True,
        choices=VALID_CHANNELS,
        help="토큰을 생성할 채널 키 (예: CH1)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="CH1~CH7 전체 채널 토큰을 순서대로 생성",
    )
    args = parser.parse_args()

    if args.all:
        for ch in VALID_CHANNELS:
            generate_token(ch)
            input(f"\n{ch} 완료. 다음 채널({VALID_CHANNELS[VALID_CHANNELS.index(ch) + 1] if ch != 'CH7' else '없음'})을 진행하려면 Enter를 누르세요... ")
    else:
        generate_token(args.channel)


if __name__ == "__main__":
    main()
