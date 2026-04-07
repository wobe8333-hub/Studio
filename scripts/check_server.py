"""서버 기본 동작 확인."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 루트 먼저
    print("루트 페이지 시도...")
    try:
        page.goto("http://localhost:7002/", wait_until="commit", timeout=15000)
        print(f"루트 로드 성공: {page.url}")
        page.screenshot(path="C:/tmp/root.png")
        print("스크린샷 저장 -> C:/tmp/root.png")
    except Exception as e:
        print(f"루트 실패: {e}")

    # API 직접 테스트
    print("\nAPI 직접 테스트...")
    for v in ["thumbnail_v1", "thumbnail_v2", "thumbnail_v3"]:
        url = f"http://localhost:7002/api/artifacts/CH1/run_CH1_1775143500/step10/{v}.png"
        try:
            resp = page.request.get(url, timeout=10000)
            print(f"  {v}.png: HTTP {resp.status} / {resp.headers.get('content-type','?')}")
        except Exception as e:
            print(f"  {v}.png: ERROR {e}")

    browser.close()
