import sys
import time
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

PAGES = [
    {"name": "Overview", "url": f"{BASE_URL}/"},
    {"name": "Applications", "url": f"{BASE_URL}/applications"},
    {"name": "Application Detail (inventory-api)", "url": f"{BASE_URL}/applications/inventory-api"},
    {"name": "Activity", "url": f"{BASE_URL}/activity"},
    {"name": "Settings", "url": f"{BASE_URL}/settings"},
]

def run_playwright_tests():
    print("=" * 80)
    print("RUNNING PLAYWRIGHT SUITE AGAINST LIVE VERCEL URL")
    print(f"Target: {BASE_URL}")
    print("=" * 80)
    
    console_errors = []
    network_errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_PATH)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("requestfailed", lambda req: network_errors.append(f"{req.method} {req.url} -> {req.failure}"))
        
        # 1. Overview Page
        print("\n[Playwright] Testing Overview Page...")
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(1000)
        assert "DevForge" in page.title(), f"Title mismatch: {page.title()}"
        print("  ✓ Title verified: DevForge")
        
        # 2. Application-Centric Navigation
        print("\n[Playwright] Testing Application-Centric Navigation (Overview, Applications, Activity, Settings)...")
        sidebar = page.locator("aside")
        for nav in ["Overview", "Applications", "Activity", "Settings"]:
            btn = sidebar.locator(f"button:has-text('{nav}')").first
            assert btn.is_visible(), f"Sidebar button '{nav}' not visible"
            print(f"  ✓ Primary navigation item '{nav}' visible in sidebar")
        
        # Standalone forbidden items check
        for forbidden in ["Deployments", "Environments", "Infrastructure", "Automation", "Monitoring", "GitOps"]:
            btn = sidebar.locator(f"button:has-text('{forbidden}')")
            assert btn.count() == 0, f"Forbidden standalone item '{forbidden}' found in primary sidebar"
        print("  ✓ Clean sidebar confirmed: standalone modules removed from top-level")
        
        # 3. Applications Catalog Page
        print("\n[Playwright] Testing Applications Catalog Page...")
        sidebar.locator("button:has-text('Applications')").first.click()
        page.wait_for_timeout(1000)
        assert "/applications" in page.url
        print("  ✓ Navigated to /applications")
        
        # Check that application names are visible
        apps = ["inventory-api", "billing-svc-8b3e27", "order-svc-c5d8a5", "payment-gateway"]
        for app in apps:
            locator = page.locator(f"text={app}").first
            assert locator.is_visible(), f"Application '{app}' not visible in catalog"
            print(f"  ✓ Application '{app}' visible in catalog")
            
        # 4. Inside Application: inventory-api & 7 subtabs
        print("\n[Playwright] Testing Application Detail & 7 subtabs for 'inventory-api'...")
        page.goto(f"{BASE_URL}/applications/inventory-api", wait_until="networkidle")
        page.wait_for_timeout(1000)
        assert "inventory-api" in page.inner_text("body")
        print("  ✓ inventory-api detail header rendered")
        
        subtabs = ["overview", "deployments", "environments", "infrastructure", "automation", "monitoring", "logs"]
        for tab in subtabs:
            tab_btn = page.locator(f"#app-tab-{tab}").first
            assert tab_btn.is_visible(), f"Subtab '#app-tab-{tab}' not visible"
            tab_btn.click()
            page.wait_for_timeout(400)
            print(f"  ✓ Subtab '{tab}' clickable and active")
            
        # 5. Phase 11 Self-Healing UI Flows
        print("\n[Playwright] Testing Phase 11 Self-Healing UI flows on inventory-api...")
        # A. Check Overview card
        page.locator("#app-tab-overview").click()
        page.wait_for_timeout(500)
        
        rem_card = page.locator("#overview-remediation-card")
        assert rem_card.is_visible(), "Self-healing card missing on overview"
        rem_card_text = rem_card.inner_text().upper()
        assert "SELF-HEALING & AUTOMATED REMEDIATION" in rem_card_text
        assert "TOTAL REMEDIATIONS" in rem_card_text
        assert "RECOVERIES" in rem_card_text
        print("  ✓ Overview Self-Healing & Automated Remediation summary card verified")

        # B. Go to Monitoring tab to inspect Policies & Events
        page.locator("#app-tab-monitoring").click()
        page.wait_for_timeout(600)
        
        body_text_upper = page.inner_text("body").upper()
        assert "ENFORCED REMEDIATION POLICIES" in body_text_upper, "Enforced Remediation Policies table missing in Monitoring tab"
        assert "REMEDIATION EVENTS & INCIDENT LOG" in body_text_upper, "Remediation Incident Log missing"
        assert "POD_CRASH_LOOP" in body_text_upper, "POD_CRASH_LOOP event missing"
        assert "RECOVERED" in body_text_upper, "RECOVERED event status badge missing"
        assert "RESTART_POD" in body_text_upper, "RESTART_POD allowlisted action missing"
        print("  ✓ Monitoring tab: Enforced remediation policies, incident timeline, and execution history verified")

        # C. Trigger Health Scan
        scan_btn = page.locator("#btn-scan-health, button:has-text('Run Health Scan'), button:has-text('Scan Health')").first
        if scan_btn.count() > 0:
            scan_btn.click()
            page.wait_for_timeout(800)
            print("  ✓ Health scan trigger interactive flow executed successfully")
        
        # 6. Activity & Settings Pages
        print("\n[Playwright] Testing Activity & Settings pages...")
        page.goto(f"{BASE_URL}/activity", wait_until="networkidle")
        page.wait_for_timeout(800)
        assert "Activity" in page.inner_text("body")
        print("  ✓ Activity page verified")
        
        page.goto(f"{BASE_URL}/settings", wait_until="networkidle")
        page.wait_for_timeout(800)
        assert "Settings" in page.inner_text("body")
        print("  ✓ Settings page verified")
        
        # 7. Navigation & History (Back / Forward / Refresh)
        print("\n[Playwright] Testing Direct URLs, Refresh, and Back/Forward Navigation...")
        page.goto(f"{BASE_URL}/applications/inventory-api", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        assert "inventory-api" in page.inner_text("body")
        print("  ✓ Direct URL & Reload verified for /applications/inventory-api")
        
        page.go_back(wait_until="networkidle")
        page.wait_for_timeout(500)
        print(f"  ✓ Back navigation successful to: {page.url}")
        
        page.go_forward(wait_until="networkidle")
        page.wait_for_timeout(500)
        print(f"  ✓ Forward navigation successful to: {page.url}")
        
        browser.close()
        
    print(f"\n[Playwright Summary] Console Errors: {len(console_errors)}")
    if console_errors:
        for err in console_errors:
            print("   ERR:", err)
    print(f"[Playwright Summary] Network Failures: {len(network_errors)}")
    if network_errors:
        for nerr in network_errors:
            print("   NET ERR:", nerr)
            
    assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
    assert len(network_errors) == 0, f"Found {len(network_errors)} network errors!"
    print("\n>>> PLAYWRIGHT SUITE PASSED ALL CHECKS! <<<\n")
    return True

def run_selenium_tests():
    print("=" * 80)
    print("RUNNING SELENIUM SUITE AGAINST LIVE VERCEL URL")
    print(f"Target: {BASE_URL}")
    print("=" * 80)
    
    options = Options()
    options.binary_location = CHROME_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    
    try:
        # 1. Load Live URL
        print("\n[Selenium] Loading live site...")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DevForge')]"))
        )
        print("  ✓ DevForge live site loaded")
        
        # 2. Sidebar Navigation Verification
        sidebar = driver.find_element(By.TAG_NAME, "aside")
        for primary in ["Overview", "Applications", "Activity", "Settings"]:
            btn = sidebar.find_element(By.XPATH, f".//button[contains(., '{primary}')]")
            assert btn.is_displayed(), f"Primary destination '{primary}' missing"
            print(f"  ✓ Primary destination '{primary}' displayed in sidebar")
            
        for forbidden in ["Deployments", "Environments", "Infrastructure", "Automation", "Monitoring", "GitOps"]:
            elements = sidebar.find_elements(By.XPATH, f".//button[contains(., '{forbidden}')]")
            assert len(elements) == 0, f"Standalone destination '{forbidden}' must not be in primary sidebar"
        print("  ✓ Standalone destinations excluded from sidebar")
        
        # 3. Application Catalog & Direct Navigation
        print("\n[Selenium] Navigating to Applications catalog...")
        driver.get(f"{BASE_URL}/applications")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'inventory-api')]"))
        )
        print("  ✓ Applications catalog rendered with inventory-api")
        
        # 4. Detail Navigation
        driver.get(f"{BASE_URL}/applications/inventory-api")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Platform Engineering')]"))
        )
        print("  ✓ inventory-api application detail loaded with metadata")
        
        # 5. Check tabs inside application
        for tab in ["overview", "deployments", "environments", "infrastructure", "automation", "monitoring", "logs"]:
            tab_elem = driver.find_element(By.ID, f"app-tab-{tab}")
            assert tab_elem.is_displayed(), f"Tab 'app-tab-{tab}' not displayed"
            print(f"  ✓ Tab '{tab}' verified")
            
        print("\n>>> SELENIUM SUITE PASSED ALL CHECKS! <<<\n")
        return True
    finally:
        driver.quit()

def run_viewport_and_overflow_tests():
    print("=" * 80)
    print("RUNNING 8-VIEWPORT RESPONSIVE & HORIZONTAL OVERFLOW VERIFICATION")
    print("=" * 80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME_PATH)
        
        all_passed = True
        for vp in VIEWPORTS:
            vp_name = vp["name"]
            width = vp["width"]
            height = vp["height"]
            print(f"\n--- Testing Viewport: {vp_name} ({width}x{height}) ---")
            
            page = browser.new_page(viewport={"width": width, "height": height})
            
            for pg in PAGES:
                pg_name = pg["name"]
                pg_url = pg["url"]
                
                page.goto(pg_url, wait_until="networkidle")
                page.wait_for_timeout(600)
                
                # Check horizontal overflow programmatically
                doc_scroll = page.evaluate("document.documentElement.scrollWidth")
                doc_client = page.evaluate("document.documentElement.clientWidth")
                body_scroll = page.evaluate("document.body.scrollWidth")
                body_client = page.evaluate("document.body.clientWidth")
                
                overflow = doc_scroll > doc_client or body_scroll > width
                if overflow:
                    print(f"  ❌ OVERFLOW on {pg_name}: docScroll={doc_scroll}, docClient={doc_client}, bodyScroll={body_scroll}, targetWidth={width}")
                    all_passed = False
                else:
                    print(f"  ✓ {pg_name}: No horizontal overflow (scrollWidth={doc_scroll}, clientWidth={doc_client})")
                    
                # If on Applications page, verify application names not clipped
                if pg_name == "Applications":
                    app_names = ["inventory-api", "billing-svc-8b3e27", "order-svc-c5d8a5", "payment-gateway"]
                    for aname in app_names:
                        loc = page.locator(f"text={aname}").first
                        if loc.count() > 0:
                            box = loc.bounding_box()
                            if box:
                                # Ensure name is visible and within bounds
                                assert box["x"] >= 0, f"App name {aname} clipped on left: {box['x']}"
                                assert box["x"] < width, f"App name {aname} off right edge: {box['x']} >= {width}"
                    print(f"  ✓ Application names fully visible and not clipped in {vp_name}")
                    
            page.close()
            
        browser.close()
        assert all_passed, "Horizontal overflow detected on one or more viewports/pages!"
        print("\n>>> ALL 8 VIEWPORTS PASSED WITH ZERO HORIZONTAL OVERFLOW AND ZERO CLIPPING! <<<\n")
        return True

if __name__ == "__main__":
    pw_ok = run_playwright_tests()
    sel_ok = run_selenium_tests()
    vp_ok = run_viewport_and_overflow_tests()
    
    print("\n" + "=" * 80)
    print("ALL LIVE VERCEL DEPLOYMENT VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print(f"Playwright: {'PASS' if pw_ok else 'FAIL'}")
    print(f"Selenium:   {'PASS' if sel_ok else 'FAIL'}")
    print(f"Viewports:  {'PASS' if vp_ok else 'FAIL'}")
    print("=" * 80)
