"""
Cleanup Forbidden Files Script

금지 파일/폴더를 삭제합니다.
"""

import sys
from pathlib import Path
import shutil


def main():
    """메인 함수"""
    repo_root = Path(__file__).resolve().parent.parent.parent
    
    deleted = []
    errors = []
    
    # backend/.env
    env_file = repo_root / "backend" / ".env"
    if env_file.exists():
        try:
            env_file.unlink()
            deleted.append(str(env_file.relative_to(repo_root)))
            print(f"Deleted: {env_file.relative_to(repo_root)}")
        except Exception as e:
            errors.append(f"Failed to delete {env_file.relative_to(repo_root)}: {e}")
    
    # frontend/node_modules
    node_modules = repo_root / "frontend" / "node_modules"
    if node_modules.exists() and node_modules.is_dir():
        try:
            shutil.rmtree(node_modules)
            deleted.append(str(node_modules.relative_to(repo_root)))
            print(f"Deleted: {node_modules.relative_to(repo_root)}")
        except Exception as e:
            errors.append(f"Failed to delete {node_modules.relative_to(repo_root)}: {e}")
    
    # frontend/.next
    next_dir = repo_root / "frontend" / ".next"
    if next_dir.exists() and next_dir.is_dir():
        try:
            shutil.rmtree(next_dir)
            deleted.append(str(next_dir.relative_to(repo_root)))
            print(f"Deleted: {next_dir.relative_to(repo_root)}")
        except Exception as e:
            errors.append(f"Failed to delete {next_dir.relative_to(repo_root)}: {e}")
    
    # backend/**/__pycache__/
    backend_dir = repo_root / "backend"
    pycache_count = 0
    for pycache_dir in backend_dir.rglob("__pycache__"):
        try:
            if pycache_dir.is_dir():
                shutil.rmtree(pycache_dir)
                pycache_count += 1
        except Exception as e:
            errors.append(f"Failed to delete {pycache_dir.relative_to(repo_root)}: {e}")
    
    if pycache_count > 0:
        deleted.append(f"backend/**/__pycache__/ ({pycache_count} directories)")
        print(f"Deleted: {pycache_count} __pycache__ directories")
    
    # backend/**/*.pyc
    pyc_count = 0
    for pyc_file in backend_dir.rglob("*.pyc"):
        try:
            if pyc_file.is_file():
                pyc_file.unlink()
                pyc_count += 1
        except Exception as e:
            errors.append(f"Failed to delete {pyc_file.relative_to(repo_root)}: {e}")
    
    if pyc_count > 0:
        deleted.append(f"backend/**/*.pyc ({pyc_count} files)")
        print(f"Deleted: {pyc_count} *.pyc files")
    
    # 결과 출력
    print("\n" + "=" * 60)
    total_items = len([d for d in deleted if not (d.startswith('backend/**') or 'directories' in d or 'files' in d)])
    print(f"Deleted: {total_items} items")
    if pycache_count > 0:
        print(f"  - __pycache__ directories: {pycache_count}")
    if pyc_count > 0:
        print(f"  - *.pyc files: {pyc_count}")
    
    if errors:
        print(f"\nErrors: {len(errors)}")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... 외 {len(errors) - 10}개 오류")
    
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

