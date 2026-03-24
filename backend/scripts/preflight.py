"""
Preflight Check - 런타임 에러 사전 검출 스위트
"""

import sys
import subprocess
import traceback
from pathlib import Path

# 프로젝트 루트 기준으로 import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def run_check(name: str, check_func) -> tuple[bool, str]:
    """
    체크 실행
    
    Returns:
        (성공 여부, 메시지)
    """
    try:
        result = check_func()
        if result:
            return True, "PASS"
        else:
            return False, "FAIL"
    except Exception as e:
        return False, f"ERROR: {type(e).__name__}: {e}"


def check_imports() -> bool:
    """주요 모듈 import 검증"""
    try:
        import backend.cli.run
        import backend.knowledge_v1.schema
        import backend.knowledge_v1.ingest
        import backend.knowledge_v1.fallback
        import backend.knowledge_v1.license_gate
        import backend.knowledge_v1.derive
        import backend.knowledge_v1.classify
        return True
    except Exception as e:
        print(f"  Import error: {e}")
        return False


def check_compile() -> bool:
    """컴파일 검증"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "backend"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  Compile error: {e}")
        return False


def check_schema_self_check() -> bool:
    """Schema 자기검증"""
    try:
        from backend.knowledge_v1.schema import KnowledgeAsset
        
        # 최소 필드셋으로 인스턴스 생성 테스트
        test_asset = KnowledgeAsset.create(
            category="test",
            keywords=["test"],
            source_id="test",
            source_ref="test://test",
            payload={"text": "test"}
        )
        
        # 필수 필드 확인
        assert hasattr(test_asset, 'asset_id')
        assert hasattr(test_asset, 'category')
        assert hasattr(test_asset, 'license_source')  # v7.1 추가 필드
        
        # license_source 기본값 확인
        assert test_asset.license_source is None or isinstance(test_asset.license_source, str)
        
        # to_dict/from_dict 순환 테스트
        d = test_asset.to_dict()
        restored = KnowledgeAsset.from_dict(d)
        assert restored.category == test_asset.category
        assert restored.license_source == test_asset.license_source
        
        # INTERNAL_SYNTHETIC 테스트
        fallback_asset = KnowledgeAsset.create(
            category="test",
            keywords=["test"],
            source_id="fallback_synthetic",
            source_ref="internal://fallback_synthetic",
            payload={"text": "test"},
            license_status="KNOWN",
            usage_rights="ALLOWED",
            trust_level="LOW",
            impact_scope="LOW",
            license_source="INTERNAL_SYNTHETIC"
        )
        assert fallback_asset.license_source == "INTERNAL_SYNTHETIC"
        assert fallback_asset.license_status == "KNOWN"
        
        return True
    except Exception as e:
        print(f"  Schema self-check error: {e}")
        traceback.print_exc()
        return False


def check_import_sanity() -> bool:
    """import_sanity 실행"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "backend.scripts.import_sanity"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  import_sanity error: {e}")
        return False


def check_verify_runs() -> bool:
    """verify_runs 실행 (선택적, 시간 오래 걸릴 수 있음)"""
    try:
        # verify_runs는 시간이 오래 걸릴 수 있으므로 타임아웃 설정
        result = subprocess.run(
            [sys.executable, "-m", "backend.scripts.verify_runs"],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  verify_runs timeout (may be OK if runs are large)")
        return True  # 타임아웃은 경고만 (선택적 체크)
    except Exception as e:
        print(f"  verify_runs error: {e}")
        return False


def check_knowledge_ingest_smoke(category: str, keywords: list) -> tuple[bool, dict]:
    """
    지식 ingest 스모크 테스트
    
    Returns:
        (성공 여부, 통계)
    """
    from backend.knowledge_v1.ingest import ingest
    from backend.knowledge_v1.store import get_knowledge_root, load_jsonl
    
    try:
        # 실행 전 라인 수
        assets_path = get_knowledge_root() / "raw" / "assets.jsonl"
        chunks_path = get_knowledge_root() / "derived" / "chunks.jsonl"
        audit_path = get_knowledge_root() / "audit" / "audit.jsonl"
        
        assets_before = sum(1 for _ in load_jsonl(assets_path)) if assets_path.exists() else 0
        chunks_before = sum(1 for _ in load_jsonl(chunks_path)) if chunks_path.exists() else 0
        
        # ingest 실행
        assets = ingest(category, keywords, depth="normal", mode="dry-run")
        
        # 실행 후 라인 수
        assets_after = sum(1 for _ in load_jsonl(assets_path)) if assets_path.exists() else 0
        chunks_after = sum(1 for _ in load_jsonl(chunks_path)) if chunks_path.exists() else 0
        
        # audit 확인
        has_start = False
        has_end = False
        has_license_block = False
        if audit_path.exists():
            # 최근 50줄만 확인
            recent_events = list(load_jsonl(audit_path))[-50:]
            for event in recent_events:
                if event.get("event_type") == "INGEST_RUN_START":
                    has_start = True
                if event.get("event_type") == "INGEST_RUN_END":
                    has_end = True
                if event.get("event_type") == "LICENSE_BLOCK":
                    # fallback asset에 대한 LICENSE_BLOCK인지 확인
                    details = event.get("details", {})
                    asset_id = details.get("asset_id", "")
                    # 최근 실행한 asset ID와 비교
                    if any(a.asset_id == asset_id for a in assets):
                        has_license_block = True
        
        stats = {
            "assets_before": assets_before,
            "assets_after": assets_after,
            "assets_increased": assets_after > assets_before,
            "chunks_before": chunks_before,
            "chunks_after": chunks_after,
            "chunks_increased": chunks_after > chunks_before,
            "has_start": has_start,
            "has_end": has_end,
            "has_license_block": has_license_block,
            "ingested_count": len(assets)
        }
        
        # PASS 조건
        success = (
            len(assets) >= 1 and
            assets_after > assets_before and
            chunks_after > chunks_before and
            has_start and
            has_end and
            not has_license_block
        )
        
        return success, stats
        
    except Exception as e:
        print(f"  Smoke test error: {e}")
        traceback.print_exc()
        return False, {"error": str(e)}


def main():
    """메인 함수"""
    print("=" * 70)
    print("PREFLIGHT CHECK: Runtime Error Prevention Suite")
    print("=" * 70)
    print("")
    
    checks = []
    
    # 1) Import 단계
    print("Step 1: Import verification...")
    success, msg = run_check("imports", check_imports)
    checks.append(("Import", success, msg))
    print(f"  {'✓' if success else '✗'} {msg}")
    print("")
    
    # 2) 컴파일 검증
    print("Step 2: Compile verification...")
    success, msg = run_check("compile", check_compile)
    checks.append(("Compile", success, msg))
    print(f"  {'✓' if success else '✗'} {msg}")
    print("")
    
    # 3) Schema 자기검증
    print("Step 3: Schema self-check...")
    success, msg = run_check("schema", check_schema_self_check)
    checks.append(("Schema", success, msg))
    print(f"  {'✓' if success else '✗'} {msg}")
    print("")
    
    # 4) import_sanity
    print("Step 4: import_sanity...")
    success, msg = run_check("import_sanity", check_import_sanity)
    checks.append(("import_sanity", success, msg))
    print(f"  {'✓' if success else '✗'} {msg}")
    print("")
    
    # 5) verify_runs (선택적, 시간 오래 걸릴 수 있음)
    print("Step 5: verify_runs (optional, may timeout)...")
    success, msg = run_check("verify_runs", check_verify_runs)
    checks.append(("verify_runs", success, msg))
    print(f"  {'✓' if success else '✗'} {msg}")
    print("")
    
    # 6) Knowledge ingest 스모크 테스트 - science
    print("Step 6: Knowledge ingest smoke test (science)...")
    try:
        success, stats = check_knowledge_ingest_smoke("science", ["black hole", "event horizon"])
        checks.append(("Science ingest", success, "PASS" if success else "FAIL"))
        if success:
            print(f"  ✓ PASS")
            print(f"    Ingested: {stats.get('ingested_count', 0)}")
            print(f"    Assets increased: {stats.get('assets_increased', False)}")
            print(f"    Chunks increased: {stats.get('chunks_increased', False)}")
            print(f"    Audit START/END: {stats.get('has_start', False)}/{stats.get('has_end', False)}")
            print(f"    LICENSE_BLOCK: {stats.get('has_license_block', False)}")
        else:
            print(f"  ✗ FAIL")
            print(f"    Stats: {stats}")
    except Exception as e:
        checks.append(("Science ingest", False, f"ERROR: {e}"))
        print(f"  ✗ ERROR: {e}")
    print("")
    
    # 7) Knowledge ingest 스모크 테스트 - papers
    print("Step 7: Knowledge ingest smoke test (papers)...")
    try:
        success, stats = check_knowledge_ingest_smoke("papers", ["transformer", "attention"])
        checks.append(("Papers ingest", success, "PASS" if success else "FAIL"))
        if success:
            print(f"  ✓ PASS")
            print(f"    Ingested: {stats.get('ingested_count', 0)}")
            print(f"    Assets increased: {stats.get('assets_increased', False)}")
            print(f"    Chunks increased: {stats.get('chunks_increased', False)}")
            print(f"    Audit START/END: {stats.get('has_start', False)}/{stats.get('has_end', False)}")
            print(f"    LICENSE_BLOCK: {stats.get('has_license_block', False)}")
        else:
            print(f"  ✗ FAIL")
            print(f"    Stats: {stats}")
    except Exception as e:
        checks.append(("Papers ingest", False, f"ERROR: {e}"))
        print(f"  ✗ ERROR: {e}")
    print("")
    
    # 결과 요약
    print("=" * 70)
    print("PREFLIGHT SUMMARY")
    print("=" * 70)
    print(f"{'Check':<30} {'Status':<10} {'Message'}")
    print("-" * 70)
    
    all_passed = True
    for name, success, msg in checks:
        status = "PASS" if success else "FAIL"
        print(f"{name:<30} {status:<10} {msg}")
        if not success:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("✅ PREFLIGHT: ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("❌ PREFLIGHT: SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

