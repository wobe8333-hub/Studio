"""
Manifest Repair - 깨진 manifest 자동 복구

기능:
- JSON 파싱 실패 시 자동 복구 시도
- 제어문자 제거
- 경로 문자열 정규화
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional

from backend.utils.json_sanitize import sanitize_json_obj


def load_manifest_with_repair(path: Path) -> Optional[Dict]:
    """
    깨진 manifest를 자동으로 읽고 복구
    
    Args:
        path: manifest.json 경로
    
    Returns:
        Optional[Dict]: 복구된 manifest (실패 시 None)
    """
    if not path.exists():
        return None
    
    try:
        # 1) UTF-8로 raw 읽기
        raw_content = path.read_text(encoding='utf-8')
    except Exception:
        try:
            # UTF-8 실패 시 다른 인코딩 시도
            raw_content = path.read_text(encoding='utf-8-sig')
        except Exception:
            return None
    
    # 2) 먼저 정상 json.loads 시도
    try:
        manifest = json.loads(raw_content)
        # 성공 시 sanitize 적용
        return sanitize_json_obj(manifest)
    except json.JSONDecodeError:
        pass  # 복구 시도로 진행
    
    # 3) 복구 시도
    try:
        # 제어문자 제거 (단, \n, \r, \t는 공백으로 치환)
        repaired = raw_content
        repaired = repaired.replace('\r', ' ')
        repaired = repaired.replace('\n', ' ')
        repaired = repaired.replace('\t', ' ')
        
        # 나머지 제어문자(0x00~0x1F) 제거
        repaired = ''.join(
            char for char in repaired
            if ord(char) >= 0x20 or char in ['\n', '\r', '\t']
        )
        
        # 경로 후보 영역 정규화
        # '\\\\'는 유지 (이미 이스케이프된 백슬래시)
        # ':\' 패턴을 ':/'로
        repaired = re.sub(r':\\', ':/', repaired)
        
        # 특정 경로 패턴 정규화
        path_replacements = [
            (r'\\Users\\', '/Users/'),
            (r'\\backend\\', '/backend/'),
            (r'\\output\\', '/output/'),
            (r'\\runs\\', '/runs/'),
            (r'\\renders\\', '/renders/'),
            (r'\\verify\\', '/verify/'),
            (r'\\step\d+\\', lambda m: f'/step{m.group(0)[-2]}/'),  # \step1\ -> /step1/
        ]
        
        for pattern, replacement in path_replacements:
            if callable(replacement):
                repaired = re.sub(pattern, replacement, repaired)
            else:
                repaired = repaired.replace(pattern, replacement)
        
        # 연속된 백슬래시를 슬래시로 (단, 이미 이스케이프된 것은 제외)
        # 단순화: 문자열 내부의 단일 백슬래시를 슬래시로
        # 주의: JSON 문자열 내부의 이스케이프는 유지해야 함
        # 안전한 방법: 경로 패턴만 치환 (이미 위에서 처리)
        
        # 4) json.loads 재시도
        manifest = json.loads(repaired)
        
        # 5) sanitize 적용
        return sanitize_json_obj(manifest)
    
    except Exception:
        # 복구 실패
        return None

