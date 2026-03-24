"""
Knowledge v1 Scheduler - 매일 오후 5시 자동 적재 스케줄러
"""

import os
import time
import signal
import sys
from datetime import datetime, time as dt_time, timedelta
from typing import List, Optional
from pathlib import Path

from backend.knowledge_v1.ingest import ingest
from backend.knowledge_v1.license_gate import apply_license_gate
from backend.knowledge_v1.derive import derive
from backend.knowledge_v1.classify import classify
from backend.knowledge_v1.store import get_knowledge_root, atomic_write_json
from backend.knowledge_v1.audit import log_event


def get_local_now() -> datetime:
    """로컬 시간 기준 현재 시각"""
    return datetime.now()


def get_next_run_datetime() -> datetime:
    """
    다음 실행 시각 계산 (로컬 시간 기준 17:00)
    
    Returns:
        datetime: 다음 실행 시각
    """
    now = get_local_now()
    target_time = dt_time(17, 0)  # 17:00
    
    # 오늘 17:00
    today_target = datetime.combine(now.date(), target_time)
    
    # 현재 시간이 17:00 이전이면 오늘 17:00
    if now < today_target:
        return today_target
    else:
        # 현재 시간이 17:00 이후면 내일 17:00
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, target_time)


def load_scheduler_state() -> dict:
    """스케줄러 상태 로드"""
    from backend.knowledge_v1.store import load_scheduler_state as _load
    return _load()


def save_scheduler_state(state: dict) -> None:
    """스케줄러 상태 저장 (atomic write)"""
    from backend.knowledge_v1.store import save_scheduler_state as _save
    _save(state)


def should_run_today(force: bool = False) -> bool:
    """
    오늘 실행해야 하는지 확인
    
    Args:
        force: 강제 실행 (환경변수 FORCE_RUN_TODAY=1)
    
    Returns:
        bool: 실행 여부
    """
    if force or os.getenv("FORCE_RUN_TODAY") == "1":
        return True
    
    state = load_scheduler_state()
    today = get_local_now().date().isoformat()
    
    # 오늘 이미 실행했으면 False
    if state.get("last_run_date") == today:
        return False
    
    return True


def run_scheduled_ingest(category: str, keywords: List[str], mode: str = "dry-run") -> bool:
    """
    스케줄된 적재 실행
    
    Returns:
        bool: 성공 여부
    """
    try:
        # ingest 실행
        assets = ingest(category, keywords, depth="normal", mode=mode)
        
        # license_gate + derive + classify
        for asset in assets:
            passed, reason = apply_license_gate(asset)
            if passed:
                derive(asset)
                classify(asset, "normal")
        
        log_event("SCHEDULER_RUN", {
            "category": category,
            "keywords": keywords,
            "target_time": "17:00",
            "result": "SUCCESS",
            "assets_count": len(assets)
        })
        
        return True
    except Exception as e:
        log_event("SCHEDULER_FAIL", {
            "category": category,
            "keywords": keywords,
            "target_time": "17:00",
            "result": "FAIL",
            "error": str(e)
        })
        return False


def start_daily_scheduler(category: str, keywords: List[str], mode: str = "dry-run") -> None:
    """
    매일 오후 5시 자동 적재 스케줄러 시작
    
    Args:
        category: 카테고리
        keywords: 키워드 리스트
        mode: 모드 (dry-run|http)
    """
    # 시작 이벤트 기록
    log_event("SCHEDULER_START", {
        "category": category,
        "keywords": keywords,
        "target_time": "17:00",
        "mode": mode
    })
    
    print(f"✅ KNOWLEDGE SCHEDULER: STARTED")
    print(f"Category: {category}")
    print(f"Keywords: {', '.join(keywords)}")
    print(f"Target time: 17:00 (local time)")
    print(f"Mode: {mode}")
    print(f"Press Ctrl+C to stop")
    print("")
    
    # Ctrl+C 핸들러
    def signal_handler(sig, frame):
        log_event("SCHEDULER_STOP", {
            "category": category,
            "keywords": keywords,
            "target_time": "17:00"
        })
        print("\n✅ KNOWLEDGE SCHEDULER: STOPPED")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 메인 루프
    while True:
        try:
            now = get_local_now()
            next_run = get_next_run_datetime()
            today = now.date().isoformat()
            
            # 강제 실행 모드 또는 실행 시간 도달
            force_run = os.getenv("FORCE_RUN_TODAY") == "1"
            should_run = force_run or (now >= next_run and should_run_today(force=force_run))
            
            if should_run:
                state = load_scheduler_state()
                
                # 오늘 이미 실행했는지 재확인 (race condition 방지)
                if not force_run and state.get("last_run_date") == today:
                    time.sleep(30)
                    continue
                
                # 실행
                success = run_scheduled_ingest(category, keywords, mode)
                
                # 상태 업데이트
                state["last_run_date"] = today
                state["last_run_status"] = "SUCCESS" if success else "FAIL"
                save_scheduler_state(state)
                
                if force_run:
                    # 강제 실행 모드는 1회만 실행하고 종료
                    print(f"✅ FORCE RUN COMPLETED: {today}")
                    break
                else:
                    print(f"✅ SCHEDULED RUN COMPLETED: {today} at {now.strftime('%H:%M:%S')}")
            
            # 30초 대기
            time.sleep(30)
            
        except KeyboardInterrupt:
            signal_handler(None, None)
            break
        except Exception as e:
            print(f"ERROR in scheduler loop: {e}")
            time.sleep(30)

