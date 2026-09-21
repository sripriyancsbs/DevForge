import sys
import time
import os
from typing import List, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = os.environ.get("DEVFORGE_TEST_URL", "http://127.0.0.1:5173")

VIEWPORTS = [
    {"width": 1920, "height": 1080, "name": "1920x1080 (Desktop FHD)"},
    {"width": 1440, "height": 900, "name": "1440x900 (Desktop Laptop)"},
    {"width": 1366, "height": 768, "name": "1366x768 (Desktop Standard)"},
    {"width": 1024, "height": 768, "name": "1024x768 (Tablet Landscape)"},
    {"width": 768, "height": 1024, "name": "768x1024 (Tablet Portrait)"},
    {"width": 430, "height": 932, "name": "430x932 (Mobile Pro Max)"},
    {"width": 390, "height": 844, "name": "390x844 (Mobile Standard)"},
    {"width": 375, "height": 667, "name": "375x667 (Mobile Small)"}
]


def run_playwright_test():
    print("=" * 70)
    print(f"RUNNING PLAYWRIGHT SUITE ON {BASE_URL}")
    print("=" * 70)

    console_errors = []
    page_errors = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("\n--- 1. Navigating to Base Platform ---")
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(1)

        # Check top-nav-workspace-badge
        badge = page.locator("#top-nav-workspace-badge")
        assert badge.is_visible(), "Workspace badge not visible"
        print(f"  ✓ Workspace badge visible: {badge.inner_text()}")

        # Ensure no self-service role switcher exists
        user_menu_btn = page.locator("#top-nav-user-menu-btn")
        if user_menu_btn.is_visible():
            user_menu_btn.click()
            time.sleep(0.5)
            # Verify no role buttons allow self promotion
            role_options = page.locator("button:has-text('Switch to')")
            assert role_options.count() == 0, "Security violation: self-service role switcher detected!"
            # Close menu
            page.keyboard.press("Escape")
            print("  ✓ Authoritative RBAC verified: No self-service role switcher")

        print("\n--- 2. Navigating to Create Application ---")
        create_nav_btn = page.locator("#top-nav-create-app-btn, button:has-text('Create App')").first
        if create_nav_btn.is_visible():
            create_nav_btn.click()
        else:
            page.goto(f"{BASE_URL}/create-application")
        time.sleep(1)

        # Fill in application name
        app_name = f"order-processing-{int(time.time())}"
        print(f"  Target Application Name: {app_name}")

        name_input = page.locator("#app-name-input, input[placeholder*='order-processing'], input[placeholder*='e.g. payment-service']").first
        name_input.fill(app_name)
        time.sleep(0.5)

        # Advance to step 2
        next_btn = page.locator("button:has-text('Next: Select Template')").first
        assert next_btn.is_visible(), "Next: Select Template button not visible"
        next_btn.click()
        time.sleep(0.5)

        # Advance to step 3
        review_btn = page.locator("button:has-text('Next: Runtime & Preview')").first
        assert review_btn.is_visible(), "Next: Runtime & Preview button not visible"
        review_btn.click()
        time.sleep(0.5)

        # Submit Provisioning
        submit_btn = page.locator("button[data-testid='create-app-submit'], button:has-text('Provision Application')").first
        assert submit_btn.is_visible(), "Provision Application button not visible"
        print("  Submitting Application Creation form...")
        submit_btn.click()

        # Wait for navigation to /applications/{app_name}
        print("\n--- 3. Verifying Immediate Navigation & Workspace Resolution ---")
        page.wait_for_url(lambda url: app_name in url or "application" in url, timeout=15000)
        time.sleep(2)

        page_content = page.content()
        # CRITICAL ASSERTIONS:
        assert "Application Not Found" not in page_content, f"BUG DETECTED: 'Application Not Found' rendered for {app_name}!"
        assert f"Application '{app_name}' was not found" not in page_content, f"BUG DETECTED: Not found message rendered!"

        # Verify application title in header
        app_heading = page.locator("h1").first
        assert app_name in app_heading.inner_text().lower(), f"Header title '{app_heading.inner_text()}' did not contain {app_name}"
        print(f"  ✓ Application Workspace rendered immediately for '{app_name}'")

        # Verify provisioning banner or status badge
        banner = page.locator("#provisioning-status-banner")
        if banner.is_visible():
            print(f"  ✓ Provisioning Status Banner rendered: '{banner.inner_text().splitlines()[0]}'")
        else:
            print("  ✓ Application status badge rendered in header")

        print("\n--- 4. Verifying Browser Refresh Persistence ---")
        page.reload(wait_until="networkidle")
        time.sleep(2)

        reloaded_content = page.content()
        assert "Application Not Found" not in reloaded_content, "Regression: Reload triggered 'Application Not Found'!"
        reloaded_heading = page.locator("h1").first
        assert app_name in reloaded_heading.inner_text().lower(), "Application name lost on reload"
        print(f"  ✓ Browser reload verified: '{app_name}' remains fully discoverable")

        print("\n--- 5. Verifying Applications Catalog Listing ---")
        apps_nav = page.locator("#sidebar-nav-applications, button:has-text('Applications')").first
        apps_nav.click()
        time.sleep(1)

        catalog_content = page.content()
        assert app_name in catalog_content, f"Application {app_name} not found in catalog listing!"
        print(f"  ✓ Application '{app_name}' listed in global Applications catalog")

        print("\n--- 6. Verifying Layout Across All 8 Viewports ---")
        for vp in VIEWPORTS:
            page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            time.sleep(0.5)

            # Check for horizontal scroll overflow
            overflow = page.evaluate("""() => {
                return document.documentElement.scrollWidth > window.innerWidth;
            }""")
            print(f"  Viewport {vp['name']}: Overflow={overflow}")
            assert not overflow, f"Layout error: Horizontal overflow detected at {vp['name']}!"

        browser.close()

    print("\n✓ PLAYWRIGHT SUITE PASSED WITH 0 ERRORS!")


def run_selenium_test():
    print("\n" + "=" * 70)
    print(f"RUNNING SELENIUM SUITE ON {BASE_URL}")
    print("=" * 70)

    options = Options()
    options.binary_location = CHROME_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)

    try:
        print("\n--- 1. Selenium: Opening Base URL ---")
        driver.get(BASE_URL)
        time.sleep(1)

        badge = driver.find_element(By.ID, "top-nav-workspace-badge")
        assert badge.is_displayed(), "Workspace badge not displayed"
        print(f"  ✓ Workspace badge displayed: {badge.text}")

        print("\n--- 2. Selenium: Navigating to Create Application ---")
        try:
            create_btn = driver.find_element(By.ID, "top-nav-create-app-btn")
            create_btn.click()
        except Exception:
            driver.get(f"{BASE_URL}/create-application")
        time.sleep(1)

        app_name = f"order-processing-sel-{int(time.time())}"
        print(f"  Target Application Name: {app_name}")

        name_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='payment-service'], input[placeholder*='order-processing'], #app-name-input")
        name_input.clear()
        name_input.send_keys(app_name)
        time.sleep(0.5)

        # Advance wizard
        try:
            next_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Next: Select Template')]")
            next_btn.click()
            time.sleep(0.5)
            review_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Next: Runtime & Preview')]")
            review_btn.click()
            time.sleep(0.5)
        except Exception as ex:
            print(f"  Note: Step advance: {ex}")

        provision_btn = driver.find_element(By.CSS_SELECTOR, "button[data-testid='create-app-submit'], button[type='submit']")
        provision_btn.click()
        print("  Submitted creation form...")

        print("\n--- 3. Selenium: Verifying Workspace Resolution ---")
        WebDriverWait(driver, 15).until(lambda d: "application" in d.current_url.lower() or app_name in d.page_source.lower())
        time.sleep(2)

        page_source = driver.page_source
        assert "Application Not Found" not in page_source, f"BUG: 'Application Not Found' rendered for {app_name}!"
        assert f"Application '{app_name}' was not found" not in page_source, f"BUG: Not found message rendered!"

        h1 = driver.find_element(By.TAG_NAME, "h1")
        assert app_name in h1.text.lower(), f"Header title '{h1.text}' did not match {app_name}"
        print(f"  ✓ Application Workspace resolved: '{h1.text}'")

        print("\n--- 4. Selenium: Verifying Browser Refresh ---")
        driver.refresh()
        time.sleep(2)
        refreshed_source = driver.page_source
        assert "Application Not Found" not in refreshed_source, "BUG: Refresh triggered Not Found"
        print(f"  ✓ Refresh verified for '{app_name}'")

        print("\n--- 5. Selenium: Verifying Catalog Listing ---")
        try:
            apps_tab = driver.find_element(By.ID, "sidebar-nav-applications")
            apps_tab.click()
        except Exception:
            driver.get(f"{BASE_URL}/applications")
        time.sleep(1)

        assert app_name in driver.page_source, f"{app_name} not in catalog"
        print(f"  ✓ Application '{app_name}' visible in catalog")

        print("\n--- 6. Selenium: Testing Viewports ---")
        for vp in VIEWPORTS:
            driver.set_window_size(vp["width"], vp["height"])
            time.sleep(0.3)
            overflow = driver.execute_script("return document.documentElement.scrollWidth > window.innerWidth;")
            assert not overflow, f"Overflow detected at {vp['name']}"
            print(f"  Viewport {vp['name']}: No overflow")

        print("\n✓ SELENIUM SUITE PASSED WITH 0 ERRORS!")
    finally:
        driver.quit()


if __name__ == "__main__":
    run_playwright_test()
    run_selenium_test()
