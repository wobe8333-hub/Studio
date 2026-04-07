"""대시보드 썸네일 탭 Playwright 검증 스크립트."""
import sys
from playwright.sync_api import sync_playwright

RUN_URL = "http://localhost:7002/runs/CH1/run_CH1_1775143500"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # 1. Run 상세 페이지 이동
        print(f"[1] 페이지 이동: {RUN_URL}")
        page.goto(RUN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # 2. 스크린샷 확인
        page.screenshot(path="C:/tmp/run_page.png", full_page=False)
        print("[2] 초기 스크린샷 저장 -> C:/tmp/run_page.png")

        # 3. 탭 목록 확인
        tabs = page.locator("button").all()
        tab_texts = [t.inner_text().strip() for t in tabs if t.inner_text().strip()]
        print(f"[3] 버튼 목록: {tab_texts[:20]}")

        # 4. 썸네일 탭 클릭
        thumb_tab = page.get_by_role("button", name="썸네일")
        if thumb_tab.count() == 0:
            thumb_tab = page.locator("button", has_text="썸네일")

        if thumb_tab.count() > 0:
            print("[4] 썸네일 탭 발견 -> 클릭")
            thumb_tab.first.click()
            page.wait_for_timeout(2000)
        else:
            print("[4] 썸네일 탭 없음")
            content = page.content()
            for kw in ["썸네일", "thumbnail", "step10"]:
                idx = content.lower().find(kw.lower())
                if idx >= 0:
                    print(f"  '{kw}' at {idx}: ...{content[max(0,idx-30):idx+80]}...")

        # 5. 클릭 후 스크린샷
        page.screenshot(path="C:/tmp/thumbnail_tab.png", full_page=False)
        print("[5] 썸네일 탭 스크린샷 -> C:/tmp/thumbnail_tab.png")

        # 6. img 태그에서 thumbnail_v 이미지 확인
        images = page.locator("img").all()
        thumb_imgs = []
        for img in images:
            src = img.get_attribute("src") or ""
            if "thumbnail" in src.lower() or "step10" in src.lower():
                thumb_imgs.append(src)
        print(f"[6] 썸네일 img 태그: {thumb_imgs}")

        # 7. 아티팩트 API 직접 HTTP 테스트
        print("\n[7] 아티팩트 API 직접 테스트:")
        api_results = {}
        for v in ["thumbnail_v1", "thumbnail_v2", "thumbnail_v3"]:
            api_url = (
                f"http://localhost:7002/api/artifacts/"
                f"CH1/run_CH1_1775143500/step10/{v}.png"
            )
            resp = page.request.get(api_url)
            ct = resp.headers.get("content-type", "unknown")
            api_results[v] = resp.status
            print(f"  {v}.png -> HTTP {resp.status} / {ct}")

        browser.close()

        # 결과 판정
        print("\n=== 검증 결과 ===")
        api_ok = all(s == 200 for s in api_results.values())
        if thumb_imgs:
            print(f"PASS 썸네일 이미지 {len(thumb_imgs)}개 DOM 표시 확인")
        else:
            print("WARN 썸네일 img 태그 미발견 (탭 미클릭 or lazy load)")
        if api_ok:
            print("PASS 아티팩트 API 3개 모두 HTTP 200")
        else:
            print(f"FAIL API 응답 오류: {api_results}")
        return 0 if (thumb_imgs or api_ok) else 1

if __name__ == "__main__":
    sys.exit(run())
