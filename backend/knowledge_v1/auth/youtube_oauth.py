"""
YouTube OAuth 2.0 토큰 관리
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False


# OAuth 2.0 Scopes
SCOPES = [
    'https://www.googleapis.com/auth/yt-analytics.readonly',
    'https://www.googleapis.com/auth/youtube.readonly'
]


def get_oauth_client_path(default_path: Optional[str] = None) -> Path:
    """OAuth Client Secret 파일 경로 반환"""
    if default_path:
        return Path(default_path)
    
    # 환경변수 YT_OAUTH_CLIENT_FILE 지원 (1순위)
    env_path = os.getenv("YT_OAUTH_CLIENT_FILE")
    if env_path:
        return Path(env_path)
    
    # 환경변수 YT_OAUTH_CLIENT_SECRET_JSON 지원 (레거시)
    env_path = os.getenv("YT_OAUTH_CLIENT_SECRET_JSON")
    if env_path:
        return Path(env_path)
    
    # 기본 경로
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "backend" / "credentials" / "yt_oauth_client.json"


def get_oauth_token_path(default_path: Optional[str] = None) -> Path:
    """OAuth Token 파일 경로 반환"""
    if default_path:
        return Path(default_path)
    
    env_path = os.getenv("YT_OAUTH_TOKEN_JSON")
    if env_path:
        return Path(env_path)
    
    # 기본 경로
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "backend" / "credentials" / "yt_oauth_token.json"


def ensure_credentials_dir() -> Path:
    """credentials 디렉토리 생성"""
    token_path = get_oauth_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    return token_path.parent


def find_oauth_client_file() -> Optional[Path]:
    """OAuth client 파일 찾기 (프로젝트 루트 + 사용자 홈 폴더 재귀 탐색)"""
    project_root = Path(__file__).resolve().parents[3]
    
    # 환경변수 우선
    env_path = os.getenv("YT_OAUTH_CLIENT_FILE")
    if env_path:
        path = Path(env_path)
        if path.exists() and _is_valid_oauth_client_file(path):
            return path
    
    # 기존 후보 경로들
    candidates = [
        project_root / "backend" / "credentials" / "yt_oauth_client.json",
        project_root / "backend" / "credentials" / "OAuth.json",
        project_root / "OAuth.json",
        project_root / "yt_oauth_client.json"
    ]
    
    # 기존 후보 확인
    for path in candidates:
        if path.exists():
            # 파일 내용 검증
            if _is_valid_oauth_client_file(path):
                return path
    
    # glob 탐색: project_root 및 project_root/backend/credentials
    search_dirs = [
        project_root,
        project_root / "backend" / "credentials"
    ]
    
    patterns = ["*oauth*.json", "*client*.json", "OAuth*.json"]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for pattern in patterns:
            for path in search_dir.glob(pattern):
                if path.is_file() and _is_valid_oauth_client_file(path):
                    return path
    
    # 사용자 홈 폴더 탐색 (재귀, 최대 깊이 3)
    try:
        user_home = Path.home()
        if user_home.exists():
            # OAuth.json, client_secret*.json 패턴으로 탐색
            patterns_home = ["OAuth.json", "client_secret*.json"]
            for pattern in patterns_home:
                # 최대 깊이 3까지 재귀 탐색
                for path in user_home.rglob(pattern):
                    if path.is_file() and _is_valid_oauth_client_file(path):
                        return path
    except Exception:
        pass
    
    # 프로젝트 루트 재귀 탐색 (최대 깊이 3, 성능 보호)
    try:
        patterns_recursive = ["OAuth.json", "client_secret*.json"]
        for pattern in patterns_recursive:
            for path in project_root.rglob(pattern):
                # 깊이 제한 (parents 수로 계산)
                depth = len(path.relative_to(project_root).parts)
                if depth > 3:
                    continue
                if path.is_file() and _is_valid_oauth_client_file(path):
                    return path
    except Exception:
        pass
    
    return None


def ensure_oauth_client_present() -> Optional[Path]:
    """
    OAuth client 파일이 목적지에 있는지 확인하고, 없으면 자동 탐색/복사
    
    Returns:
        목적지 파일 Path (성공 시) 또는 None (실패 시)
    """
    target_path = get_oauth_client_path()
    
    # 이미 존재하고 유효하면 그대로 반환
    if target_path.exists() and _is_valid_oauth_client_file(target_path):
        return target_path
    
    # 찾기
    found = find_oauth_client_file()
    if not found:
        return None
    
    # 복사
    try:
        ensure_credentials_dir()
        import shutil
        shutil.copy2(found, target_path)
        
        # 복사 후 검증
        if target_path.exists() and _is_valid_oauth_client_file(target_path):
            return target_path
        else:
            return None
    except Exception:
        return None


def _is_valid_oauth_client_file(path: Path) -> bool:
    """OAuth client 파일 유효성 검증 (client_id, client_secret 포함 여부)"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # client_id와 client_secret 둘 다 포함되어야 함
            if "client_id" in content and "client_secret" in content:
                # JSON 파싱도 시도
                try:
                    data = json.loads(content)
                    # installed 또는 web 키가 있어야 함
                    if "installed" in data or "web" in data:
                        return True
                except Exception:
                    pass
    except Exception:
        pass
    
    return False


def load_oauth_credentials(
    client_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> Optional[Credentials]:
    """
    OAuth 자격증명 로드 및 갱신
    
    Returns:
        Credentials 객체 또는 None (OAuth 미설정/실패)
    """
    if not GOOGLE_AUTH_AVAILABLE:
        return None
    
    client_file = get_oauth_client_path(client_path)
    token_file = get_oauth_token_path(token_path)
    
    # Client 파일 확인
    if not client_file.exists():
        # 프로젝트 내에서 찾기
        found = find_oauth_client_file()
        if found:
            # yt_oauth_client.json으로 복사
            ensure_credentials_dir()
            import shutil
            shutil.copy2(found, client_file)
        else:
            return None
    
    # Token 파일이 있으면 로드, 없으면 최초 인증
    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception:
            creds = None
    else:
        # Client 파일에서 로드하여 최초 인증
        try:
            with open(client_file, 'r', encoding='utf-8') as f:
                client_config = json.load(f)
            
            # 최초 인증
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            ensure_credentials_dir()
            with open(token_file, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())
        except Exception:
            creds = None
    
    # 토큰 갱신 (만료된 경우)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # 갱신된 토큰 저장
            ensure_credentials_dir()
            with open(token_file, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())
        except Exception:
            creds = None
    
    return creds


def get_credentials_dict(
    client_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    OAuth 자격증명을 dict 형태로 반환 (레거시 호환)
    
    Returns:
        {
            "client_secret": {...},
            "token": {...}
        } 또는 None
    """
    creds = load_oauth_credentials(client_path, token_path)
    if not creds:
        return None
    
    client_file = get_oauth_client_path(client_path)
    if not client_file.exists():
        return None
    
    try:
        with open(client_file, 'r', encoding='utf-8') as f:
            client_secret = json.load(f)
        
        token_dict = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        
        return {
            "client_secret": client_secret,
            "token": token_dict
        }
    except Exception:
        return None

