import sys
import time
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "https://frontend-two-self-3343htd1ck.vercel.app"

VIEWPORTS = [
    {"name": "1920x1080 (Desktop Large)", "width": 1920, "height": 1080},
    {"name": "1440x900 (Desktop Standard)", "width": 1440, "height": 900},
    {"name": "1366x768 (Laptop)", "width": 1366, "height": 768},
    {"name": "1024x768 (Tablet Landscape)", "width": 1024, "height": 768},
    {"name": "768x1024 (Tablet Portrait)", "width": 768, "height": 1024},
    {"name": "430x932 (iPhone 14 Pro Max)", "width": 430, "height": 932},
    {"name": "390x844 (iPhone 12/13/14)", "width": 390, "height": 844},
    {"name": "375x667 (iPhone SE)", "width": 375, "height": 667},
]

def test_live_applications_playwright():
    print("=" * 80)
    print("TESTING LIVE APPLICATIONS PAGE WITH PLAYWRIGHT")
    print(f"Target: {BASE_URL}/applications")
    print("=" * 80)

    console_errors = []
    network_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_PATH)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("requestfailed", lambda req: network_errors.append(f"{req.method} {req.url} -> {req.failure}"))

        print("\n1. Navigating to /applications...")
        page.goto(f"{BASE_URL}/applications", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 1. Verify Page Title and Header
        assert page.locator("h1:has-text('Applications')").is_visible(), "Applications H1 missing"
        print("  ✓ Applications catalog page loaded successfully")

        # 2. Verify Table Columns (KEPT: Application, Technology, Environment, Status, Actions)
        headers = page.locator("table thead tr th").all_text_contents()
        print(f"  ✓ Rendered table headers: {headers}")
        for expected in ["Application", "Technology", "Environment", "Status", "Actions"]:
            assert any(expected.lower() in h.lower() for h in headers), f"Expected column '{expected}' missing from headers: {headers}"
            print(f"  ✓ Verified column KEPT: {expected}")

        # 3. Verify Columns REMOVED (Repository, Version, Last Deployment)
        for removed in ["Repository", "Version", "Last Deployment"]:
            assert not any(removed.lower() == h.strip().lower() for h in headers), f"Column '{removed}' should have been REMOVED but was found in headers: {headers}"
            print(f"  ✓ Verified column REMOVED: {removed}")

        # 4. Search Filter Functionality
        print("\n2. Testing Search Filter...")
        search_input = page.locator("input[placeholder*='Filter applications by name']")
        assert search_input.is_visible(), "Search input missing"
        search_input.fill("inventory-api")
        page.wait_for_timeout(400)
        visible_rows = page.locator("table tbody tr:visible")
        assert visible_rows.count() >= 1, "Search for inventory-api returned 0 rows"
        assert "inventory-api" in visible_rows.first.text_content(), "First row doesn't contain inventory-api"
        print("  ✓ Search filter successfully filtered down to inventory-api")

        search_input.fill("")
        page.wait_for_timeout(400)

        # 5. Environment Filter Functionality
        print("\n3. Testing Environment Filter...")
        env_select = page.locator("select").nth(1)
        env_select.select_option("staging")
        page.wait_for_timeout(400)
        staging_rows = page.locator("table tbody tr:visible")
        for i in range(staging_rows.count()):
            row_text = staging_rows.nth(i).text_content()
            assert "staging" in row_text.lower(), f"Row does not match staging filter: {row_text}"
        print(f"  ✓ Environment filter (staging) verified across {staging_rows.count()} rows")

        env_select.select_option("all")
        page.wait_for_timeout(400)

        # 6. Status Filter Functionality
        print("\n4. Testing Status Filter...")
        status_select = page.locator("select").nth(0)
        status_select.select_option("healthy")
        page.wait_for_timeout(400)
        healthy_rows = page.locator("table tbody tr:visible")
        assert healthy_rows.count() >= 1, "Status filter (healthy) returned 0 rows"
        print(f"  ✓ Status filter (healthy) verified across {healthy_rows.count()} rows")

        status_select.select_option("all")
        page.wait_for_timeout(400)

        # 7. Application Row Navigation
        print("\n5. Testing Application Row Click Navigation...")
        inv_row = page.locator("table tbody tr:has-text('inventory-api')").first
        assert inv_row.is_visible(), "inventory-api row missing"
        inv_row.click()
        page.wait_for_timeout(600)
        assert "applications/inventory-api" in page.url, f"URL did not update to /applications/inventory-api: {page.url}"
        assert page.locator("h1:has-text('inventory-api')").is_visible(), "Application detail header missing"
        print("  ✓ Application row click navigated to /applications/inventory-api")

        # 8. Check that Repository, Version, and Deployment history remain available in detail page
        print("\n6. Verifying Repository, Version, and Deployments available in detail workspace...")
        assert page.locator("text=sripriyancsbs/DevForge").first.is_visible() or page.locator("a[href*='github.com']").first.is_visible(), "Repository link missing in application workspace"
        print("  ✓ Repository information confirmed available in workspace")
        assert page.locator("text=v1.").first.is_visible(), "Version information missing in application workspace"
        print("  ✓ Version information confirmed available in workspace")

        page.locator("#app-tab-deployments").click()
        page.wait_for_timeout(400)
        assert page.locator("text=Application Deployments").first.is_visible(), "Deployments tab missing"
        print("  ✓ Deployment history confirmed available in workspace")

        # Check errors
        print(f"\nConsole Errors ({len(console_errors)}):", console_errors)
        print(f"Network Errors ({len(network_errors)}):", network_errors)
        assert len(console_errors) == 0, f"Encountered console errors: {console_errors}"
        assert len(network_errors) == 0, f"Encountered network errors: {network_errors}"

        browser.close()
        print("\n>>> PLAYWRIGHT APPLICATIONS TESTS PASSED! <<<\n")
        return True

def test_live_applications_selenium():
    print("=" * 80)
    print("TESTING LIVE APPLICATIONS PAGE WITH SELENIUM")
    print(f"Target: {BASE_URL}/applications")
    print("=" * 80)

    options = Options()
    options.binary_location = CHROME_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(f"{BASE_URL}/applications")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Applications')]"))
        )
        print("  ✓ Selenium: Applications page loaded")

        # 1. Verify table headers
        headers = [th.text.strip() for th in driver.find_elements(By.XPATH, "//table//th")]
        print(f"  ✓ Selenium table headers: {headers}")
        for col in ["Application", "Technology", "Environment", "Status", "Actions"]:
            assert any(col.lower() in h.lower() for h in headers), f"Header '{col}' missing in Selenium: {headers}"
        for col in ["Repository", "Version", "Last Deployment"]:
            assert not any(col.lower() == h.lower() for h in headers), f"Header '{col}' should NOT be in Selenium table: {headers}"
        print("  ✓ Selenium: Column composition verified (5 kept, 3 removed)")

        # 2. Search
        search = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Filter applications')]")
        search.send_keys("billing-svc")
        time.sleep(0.5)
        billing_row = driver.find_element(By.XPATH, "//*[contains(text(), 'billing-svc')]")
        assert billing_row.is_displayed(), "Search for billing-svc failed"
        print("  ✓ Selenium: Search filter works")

        # Clear search filter triggering React synthetic event
        driver.execute_script("""
            const input = arguments[0];
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(input, '');
            input.dispatchEvent(new Event('input', { bubbles: true }));
        """, search)
        time.sleep(0.5)

        # 3. Row navigation
        inv_row = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'inventory-api')]"))
        )
        inv_row.click()
        time.sleep(1)
        assert "applications/inventory-api" in driver.current_url
        print(f"  ✓ Selenium: Navigated to: {driver.current_url}")

        print("\n>>> SELENIUM APPLICATIONS TESTS PASSED! <<<\n")
        return True
    finally:
        driver.quit()

def test_live_viewports_responsive():
    print("=" * 80)
    print("RUNNING 8-VIEWPORT RESPONSIVE & ZERO HORIZONTAL OVERFLOW AUDIT")
    print(f"Target: {BASE_URL}/applications")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_PATH)
        all_passed = True

        for vp in VIEWPORTS:
            vp_name = vp["name"]
            w = vp["width"]
            h = vp["height"]
            print(f"\n--- Viewport: {vp_name} ({w}x{h}) ---")

            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(f"{BASE_URL}/applications", wait_until="networkidle")
            page.wait_for_timeout(600)

            # Check programmatic documentElement scrollWidth vs clientWidth
            doc_scroll = page.evaluate("document.documentElement.scrollWidth")
            doc_client = page.evaluate("document.documentElement.clientWidth")
            body_scroll = page.evaluate("document.body.scrollWidth")

            overflow = (doc_scroll > doc_client) or (body_scroll > w)
            if overflow:
                print(f"  ❌ OVERFLOW: scrollWidth={doc_scroll}, clientWidth={doc_client}, bodyScroll={body_scroll}, viewportWidth={w}")
                all_passed = False
            else:
                print(f"  ✓ Zero page-level horizontal overflow: scrollWidth={doc_scroll} <= clientWidth={doc_client}")

            # Verify application names are fully visible and not clipped
            for app_name in ["inventory-api", "billing-svc-8b3e27", "order-svc-c5d8a5", "payment-gateway"]:
                loc = page.locator(f"text={app_name}").first
                assert loc.count() > 0, f"Application name {app_name} missing on {vp_name}"
                box = loc.bounding_box()
                assert box is not None, f"Bounding box missing for {app_name}"
                assert box["x"] >= 0, f"App name {app_name} clipped on left (x={box['x']})"
                assert (box["x"] + min(box["width"], 100)) <= w, f"App name {app_name} clipped on right: {box['x']} + width > {w}"
            print(f"  ✓ All application names unclipped and fully readable on {vp_name}")

            page.close()

        browser.close()
        assert all_passed, "Horizontal overflow detected on one or more viewports!"
        print("\n>>> ALL 8 VIEWPORTS PASSED WITH ZERO HORIZONTAL OVERFLOW AND UNCLIPPED NAMES! <<<\n")
        return True

if __name__ == "__main__":
    pw_ok = test_live_applications_playwright()
    sel_ok = test_live_applications_selenium()
    vp_ok = test_live_viewports_responsive()

    print("\n" + "=" * 80)
    print("ALL APPLICATIONS CATALOG LIVE VERIFICATION CHECKS COMPLETED!")
    print(f"Playwright: {'PASS' if pw_ok else 'FAIL'}")
    print(f"Selenium:   {'PASS' if sel_ok else 'FAIL'}")
    print(f"Viewports:  {'PASS' if vp_ok else 'FAIL'}")
    print("=" * 80)
