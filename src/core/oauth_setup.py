"""YouTube OAuth2 인증 흐름. credentials/{ch}_token.json 생성."""
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtubepartner",
]
ROOT = Path(__file__).parent.parent.parent

def run_oauth(channel_id: str) -> None:
    creds_path = ROOT / "credentials" / f"{channel_id}_credentials.json"
    token_path = ROOT / "credentials" / f"{channel_id}_token.json"
    if not creds_path.exists():
        raise FileNotFoundError(f"credentials 없음: {creds_path}")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"OK: {channel_id} token.json 생성 -> {token_path}")
    else:
        print(f"OK: {channel_id} 기존 token.json 유효")

if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "CH1"
    print(f"[OAuth] {ch} 인증 시작...")
    run_oauth(ch)
    print(f"[OAuth] {ch} 인증 완료")
