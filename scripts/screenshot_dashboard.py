"""대시보드 썸네일 탭 스크린샷."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://localhost:7002/runs/CH1/run_CH1_1775143500",
              wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)

    # 썸네일 탭 클릭
    thumb = page.locator("button", has_text="썸네일")
    if thumb.count() > 0:
        thumb.first.click()
        page.wait_for_timeout(2000)

    page.screenshot(path="C:/tmp/dashboard_thumb.png", full_page=False)
    print("저장 완료")
    browser.close()
