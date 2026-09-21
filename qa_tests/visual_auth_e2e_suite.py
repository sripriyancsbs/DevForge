import os
import sys
import time
import random

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.environ.get("DEVFORGE_TEST_URL", "http://localhost:5173")

VIEWPORTS = [
    {"width": 1920, "height": 1080, "name": "1920x1080 (Desktop FHD)"},
    {"width": 1440, "height": 900, "name": "1440x900 (Desktop Laptop)"},
    {"width": 1366, "height": 768, "name": "1366x768 (Desktop Standard)"},
    {"width": 1024, "height": 768, "name": "1024x768 (Tablet Landscape)"},
    {"width": 768, "height": 1024, "name": "768x1024 (Tablet Portrait)"},
    {"width": 430, "height": 932, "name": "430x932 (iPhone Pro Max)"},
    {"width": 390, "height": 844, "name": "390x844 (Mobile Standard)"},
    {"width": 375, "height": 667, "name": "375x667 (Mobile Small)"}
]

def log_step(step_num: int, total: int, description: str, status: str = "PASS"):
    padded_desc = description.ljust(48, ".")
    print(f"[{step_num:02d}/{total:02d}] {padded_desc} {status}", flush=True)

def reset_backend_rate_limits():
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8000/api/v1/auth/reset-rate-limit", data=b"{}", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass

def run_playwright_suite():
    reset_backend_rate_limits()
    total_steps = 24
    print("\n" + "=" * 80)
    print("PLAYWRIGHT — ACTUALLY VISIBLE E2E SUITE (WINDOWS HEADED MODE)")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80 + "\n", flush=True)

    test_user_rand = f"testuser_{int(time.time())}_{random.randint(100, 999)}"
    test_email_rand = f"{test_user_rand}@devforge.internal"
    test_password = "SecurePassword123!"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=350,
            args=["--start-maximized"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900}, no_viewport=True)
        page = context.new_page()

        # Step 1: Open Sign In
        page.goto(f"{BASE_URL}/signin", wait_until="networkidle")
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.goto(f"{BASE_URL}/signin", wait_until="networkidle")
        page.wait_for_selector("#signin-card", timeout=8000)
        log_step(1, total_steps, "Open Sign In Page")

        # Step 2: Verify Sign In Elements
        assert page.is_visible("#signin-email-input"), "Email input missing"
        assert page.is_visible("#signin-password-input"), "Password input missing"
        assert page.is_visible("#signin-submit-btn"), "Sign in button missing"
        assert page.is_visible("#signin-to-signup-link"), "Link to signup missing"
        log_step(2, total_steps, "Verify Sign In Page Elements")

        # Step 3: Test Invalid Credentials Error
        page.fill("#signin-email-input", "invalid_user@unknown.com")
        page.fill("#signin-password-input", "WrongPassword999!")
        page.click("#signin-submit-btn")
        page.wait_for_selector("#signin-error-banner", timeout=6000)
        err_text = page.inner_text("#signin-error-banner")
        assert "Invalid" in err_text or "credentials" in err_text.lower() or "password" in err_text.lower(), f"Unexpected error: {err_text}"
        log_step(3, total_steps, "Invalid Credentials Error Display")

        # Step 4: Open Sign Up
        page.click("#signin-to-signup-link")
        page.wait_for_selector("#signup-card", timeout=6000)
        assert "/signup" in page.url
        log_step(4, total_steps, "Navigate to Sign Up Page")

        # Step 5: Password Requirements Validation (<8 chars)
        page.fill("#signup-name-input", "Test Person")
        page.fill("#signup-email-input", "short@devforge.internal")
        page.fill("#signup-password-input", "short")
        page.fill("#signup-confirm-password-input", "short")
        page.click("#signup-submit-btn")
        page.wait_for_selector("#signup-error-banner", timeout=5000)
        assert "8 characters" in page.inner_text("#signup-error-banner")
        log_step(5, total_steps, "Password Requirements Validation (<8 chars)")

        # Step 6: Password Confirmation Mismatch Validation
        page.fill("#signup-password-input", "ValidPassword123!")
        page.fill("#signup-confirm-password-input", "DifferentPassword123!")
        page.click("#signup-submit-btn")
        page.wait_for_selector("#signup-error-banner", timeout=5000)
        assert "do not match" in page.inner_text("#signup-error-banner")
        log_step(6, total_steps, "Password Mismatch Validation")

        # Step 7: Fill Valid Sign Up Form
        page.fill("#signup-name-input", "Valid New User")
        page.fill("#signup-email-input", test_email_rand)
        page.fill("#signup-password-input", test_password)
        page.fill("#signup-confirm-password-input", test_password)
        log_step(7, total_steps, "Fill Valid Sign Up Form")

        # Step 8: Submit Sign Up & Automatic Authentication
        page.click("#signup-submit-btn")
        page.wait_for_selector("#user-profile-menu-button", timeout=10000)
        log_step(8, total_steps, "Account Creation & Sign In")

        # Step 9: Verify Non-Admin Role Assigned (Safe Default)
        page.click("#user-profile-menu-button")
        page.wait_for_selector("#user-profile-role", timeout=5000)
        role_text = page.inner_text("#user-profile-role")
        assert "DEVELOPER" in role_text, f"Expected safe DEVELOPER role, got: {role_text}"
        assert "ADMIN" not in role_text
        log_step(9, total_steps, "Verify Non-ADMIN Default Role (DEVELOPER)")

        # Step 10: Verify User Menu Details
        assert page.is_visible("#user-profile-name")
        assert page.is_visible("#user-profile-email")
        assert page.is_visible("#user-profile-workspace")
        assert page.is_visible("#user-logout-button")
        log_step(10, total_steps, "Verify Authenticated User Menu Details")

        # Step 11: Verify NO Self-Service Role Switcher
        page_html = page.content()
        assert "switch-to-admin" not in page_html.lower()
        assert "role-switcher" not in page_html.lower()
        log_step(11, total_steps, "Verify No Self-Service Role Switcher")

        # Step 12: Click Logout
        page.click("#user-logout-button")
        page.wait_for_selector("#signin-card", timeout=8000)
        log_step(12, total_steps, "Click Logout & Redirect to Sign In")

        # Step 13: Verify Signed Out State (NO VIEWER role fallback)
        assert not page.is_visible("#user-profile-menu-button")
        body_text = page.inner_text("body")
        assert "Active Role: VIEWER" not in body_text
        assert "VIEWER" not in page.inner_text("header")
        log_step(13, total_steps, "Verify Unauthenticated State (NO VIEWER role)")

        # Step 14: TopNav Displays Sign In & Sign Up Buttons
        assert page.is_visible("#top-nav-signin-btn")
        assert page.is_visible("#top-nav-signup-btn")
        log_step(14, total_steps, "Verify TopNav Unauthenticated Buttons")

        # Step 15: Protected Route Redirect Check
        page.goto(f"{BASE_URL}/applications", wait_until="networkidle")
        time.sleep(0.5)
        assert "/signin" in page.url or page.is_visible("#signin-card")
        assert not page.is_visible("#applications-catalog")
        log_step(15, total_steps, "Protected Route Access Redirects to Sign In")

        # Step 16: Browser Refresh Remains Signed Out
        page.reload(wait_until="networkidle")
        assert page.is_visible("#signin-card")
        assert not page.is_visible("#user-profile-menu-button")
        log_step(16, total_steps, "Browser Refresh Remains Signed Out")

        # Step 17: Browser Back Does Not Leak Protected Data
        page.go_back()
        time.sleep(0.5)
        assert not page.is_visible("#user-profile-menu-button")
        assert page.is_visible("#signin-card") or page.is_visible("#signup-card")
        log_step(17, total_steps, "Browser Back Prevents Protected State Leak")

        # Step 18: Test Duplicate Account Rejection
        page.goto(f"{BASE_URL}/signup", wait_until="networkidle")
        page.fill("#signup-name-input", "Duplicate Attempt")
        page.fill("#signup-email-input", test_email_rand)
        page.fill("#signup-password-input", test_password)
        page.fill("#signup-confirm-password-input", test_password)
        page.click("#signup-submit-btn")
        page.wait_for_selector("#signup-error-banner", timeout=6000)
        dup_text = page.inner_text("#signup-error-banner").lower()
        assert "already" in dup_text or "exists" in dup_text, f"Expected duplicate account message, got: {dup_text}"
        log_step(18, total_steps, "Duplicate Account Registration Rejection")

        def verify_role_login(demo_btn, expected_role):
            reset_backend_rate_limits()
            page.click(demo_btn)
            time.sleep(0.4)
            page.click("#signin-submit-btn")
            for _ in range(25):
                if page.is_visible("#user-profile-menu-button"):
                    break
                if page.is_visible("#signin-error-banner"):
                    err = page.inner_text("#signin-error-banner")
                    raise AssertionError(f"Login failed for {expected_role}: {err}")
                time.sleep(0.4)
            page.wait_for_selector("#user-profile-menu-button", timeout=5000)
            page.click("#user-profile-menu-button")
            time.sleep(0.3)
            assert expected_role in page.inner_text("#user-profile-role")
            page.click("#user-logout-button")
            page.wait_for_selector("#signin-card", timeout=10000)
            time.sleep(0.4)

        # Step 19: Sign In as ADMIN
        page.goto(f"{BASE_URL}/signin", wait_until="networkidle")
        verify_role_login("#demo-account-admin", "ADMIN")
        log_step(19, total_steps, "Sign In as ADMIN & Verify Role")

        # Step 20: Sign In as OPERATOR
        verify_role_login("#demo-account-operator", "OPERATOR")
        log_step(20, total_steps, "Sign In as OPERATOR & Verify Role")

        # Step 21: Sign In as DEVELOPER
        verify_role_login("#demo-account-developer", "DEVELOPER")
        log_step(21, total_steps, "Sign In as DEVELOPER & Verify Role")

        # Step 22: Sign In as VIEWER (Authenticated Role)
        verify_role_login("#demo-account-viewer", "VIEWER")
        log_step(22, total_steps, "Sign In as VIEWER (Authenticated Role)")

        # Step 23: Full Functional Regression (ADMIN Session Navigation & Controls)
        reset_backend_rate_limits()
        page.fill("#signin-email-input", "admin@devforge.internal")
        page.fill("#signin-password-input", "AdminPassword123!")
        time.sleep(0.3)
        page.click("#signin-submit-btn")
        for _ in range(25):
            if page.is_visible("#user-profile-menu-button"):
                break
            if page.is_visible("#signin-error-banner"):
                err = page.inner_text("#signin-error-banner")
                raise AssertionError(f"Step 23 Admin login error: {err}")
            time.sleep(0.4)
        page.wait_for_selector("#user-profile-menu-button", timeout=5000)
        
        page.click("#sidebar-nav-overview")
        time.sleep(0.5)
        assert page.is_visible("#overview-stats") or "overview" in page.url or page.url.endswith("/")
        page.click("#sidebar-nav-applications")
        time.sleep(0.5)
        assert page.is_visible("#applications-page-container") or "applications" in page.url
        page.click("#sidebar-nav-activity")
        time.sleep(0.5)
        assert "activity" in page.url
        page.click("#sidebar-nav-settings")
        time.sleep(0.5)
        assert "settings" in page.url
        
        # Escape & Outside click verification
        page.click("#user-profile-menu-button")
        time.sleep(0.2)
        assert page.is_visible("#user-profile-dropdown")
        page.keyboard.press("Escape")
        time.sleep(0.2)
        assert not page.is_visible("#user-profile-dropdown")

        # Logout back to clean state
        page.click("#user-profile-menu-button")
        page.click("#user-logout-button")
        page.wait_for_selector("#signin-card", timeout=10000)
        log_step(23, total_steps, "Full Functional Regression Navigation")

        # Step 24: Responsive Audit across 8 Viewports
        overflow_errors = []
        for vp in VIEWPORTS:
            page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            time.sleep(0.3)
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            if scroll_width > client_width:
                overflow_errors.append(f"{vp['name']}: scrollWidth {scroll_width} > clientWidth {client_width}")

        assert len(overflow_errors) == 0, f"Horizontal overflow detected in viewports: {overflow_errors}"
        log_step(24, total_steps, f"Responsive Audit (8/8 Viewports, 0 Overflow)")

        browser.close()
    print("\n>>> ALL 24 PLAYWRIGHT VISIBLE TESTS PASSED <<<\n", flush=True)


def run_selenium_suite():
    total_steps = 15
    print("\n" + "=" * 80)
    print("SELENIUM — ACTUALLY VISIBLE E2E SUITE (CHROME DESKTOP WINDOW)")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80 + "\n", flush=True)

    reset_backend_rate_limits()
    opts = ChromeOptions()
    opts.add_argument("--start-maximized")
    # DO NOT add --headless!
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 10)

    try:
        # Step 1: Open Chrome & Sign In
        driver.get(f"{BASE_URL}/signin")
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.get(f"{BASE_URL}/signin")
        wait.until(EC.visibility_of_element_located((By.ID, "signin-card")))
        log_step(1, total_steps, "Open Chrome & Access /signin")

        # Step 2: Verify Inputs and Buttons
        assert driver.find_element(By.ID, "signin-email-input").is_displayed()
        assert driver.find_element(By.ID, "signin-password-input").is_displayed()
        assert driver.find_element(By.ID, "signin-submit-btn").is_displayed()
        log_step(2, total_steps, "Verify Sign In Form Visibility")

        # Step 3: Test Invalid Credentials Banner
        driver.find_element(By.ID, "signin-email-input").send_keys("bad_account@devforge.internal")
        driver.find_element(By.ID, "signin-password-input").send_keys("WrongPass123!")
        driver.find_element(By.ID, "signin-submit-btn").click()
        err_elem = wait.until(EC.visibility_of_element_located((By.ID, "signin-error-banner")))
        assert "Invalid" in err_elem.text
        log_step(3, total_steps, "Invalid Login Error Banner Validation")

        # Step 4: Navigate to Sign Up
        driver.find_element(By.ID, "signin-to-signup-link").click()
        wait.until(EC.visibility_of_element_located((By.ID, "signup-card")))
        log_step(4, total_steps, "Navigate to Sign Up Page")

        # Step 5: Password Mismatch Validation
        driver.find_element(By.ID, "signup-name-input").send_keys("Selenium Tester")
        driver.find_element(By.ID, "signup-email-input").send_keys("selenium_tester@devforge.internal")
        driver.find_element(By.ID, "signup-password-input").send_keys("Password123!")
        driver.find_element(By.ID, "signup-confirm-password-input").send_keys("DifferentPassword123!")
        driver.find_element(By.ID, "signup-submit-btn").click()
        err_msg = wait.until(EC.visibility_of_element_located((By.ID, "signup-error-banner"))).text
        assert "do not match" in err_msg
        log_step(5, total_steps, "Sign Up Password Mismatch Rejection")

        # Step 6: Complete Valid Sign Up
        reset_backend_rate_limits()
        sel_user = f"sel_user_{int(time.time())}"
        sel_email = f"{sel_user}@devforge.internal"
        driver.find_element(By.ID, "signup-email-input").clear()
        driver.find_element(By.ID, "signup-email-input").send_keys(sel_email)
        driver.find_element(By.ID, "signup-confirm-password-input").clear()
        driver.find_element(By.ID, "signup-confirm-password-input").send_keys("Password123!")
        driver.find_element(By.ID, "signup-submit-btn").click()
        log_step(6, total_steps, "Submit Valid Sign Up Form")

        # Step 7: Automatic Sign In & DEVELOPER Role Check
        wait.until(EC.visibility_of_element_located((By.ID, "user-profile-menu-button")))
        driver.find_element(By.ID, "user-profile-menu-button").click()
        role_label = wait.until(EC.visibility_of_element_located((By.ID, "user-profile-role"))).text
        assert "DEVELOPER" in role_label
        log_step(7, total_steps, "Sign In & Safe DEVELOPER Role Validation")

        # Step 8: Click Sign Out
        driver.find_element(By.ID, "user-logout-button").click()
        wait.until(EC.visibility_of_element_located((By.ID, "signin-card")))
        log_step(8, total_steps, "Logout & Session Invalidation")

        # Step 9: Verify Genuine Unauthenticated TopNav
        header_text = driver.find_element(By.TAG_NAME, "header").text
        assert "VIEWER" not in header_text
        assert driver.find_element(By.ID, "top-nav-signin-btn").is_displayed()
        assert driver.find_element(By.ID, "top-nav-signup-btn").is_displayed()
        log_step(9, total_steps, "TopNav Unauthenticated State (NO VIEWER role)")

        # Step 10: Direct URL Protection
        driver.get(f"{BASE_URL}/settings")
        time.sleep(0.5)
        assert "/signin" in driver.current_url or len(driver.find_elements(By.ID, "signin-card")) > 0
        log_step(10, total_steps, "Direct URL to /settings Redirects to /signin")

        # Step 11: Sign In as ADMIN
        reset_backend_rate_limits()
        email_in = driver.find_element(By.ID, "signin-email-input")
        email_in.clear()
        email_in.send_keys("admin@devforge.internal")
        pass_in = driver.find_element(By.ID, "signin-password-input")
        pass_in.clear()
        pass_in.send_keys("AdminPassword123!")
        driver.find_element(By.ID, "signin-submit-btn").click()
        wait.until(EC.visibility_of_element_located((By.ID, "user-profile-menu-button")))
        log_step(11, total_steps, "Sign In as ADMIN in Visible Chrome")

        # Step 12: Verify Authoritative Role ADMIN in Profile
        driver.find_element(By.ID, "user-profile-menu-button").click()
        role_info = wait.until(EC.visibility_of_element_located((By.ID, "user-profile-role"))).text
        assert "ADMIN" in role_info
        log_step(12, total_steps, "Inspect Profile: Authoritative Role ADMIN")

        # Step 13: Test Outside Click & Dropdown Closing
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(0.3)
        assert len(driver.find_elements(By.ID, "user-profile-dropdown")) == 0
        log_step(13, total_steps, "Outside Click Closes Dropdowns")

        # Step 14: Logout & Browser Back Check
        driver.find_element(By.ID, "user-profile-menu-button").click()
        driver.find_element(By.ID, "user-logout-button").click()
        wait.until(EC.visibility_of_element_located((By.ID, "signin-card")))
        driver.back()
        time.sleep(0.5)
        assert len(driver.find_elements(By.ID, "user-profile-menu-button")) == 0
        log_step(14, total_steps, "Browser Back After Logout Security Check")

        # Step 15: Responsive ScrollWidth Verification (8 viewports)
        for vp in VIEWPORTS:
            driver.set_window_size(vp["width"], vp["height"])
            time.sleep(0.2)
            sw = driver.execute_script("return document.documentElement.scrollWidth")
            cw = driver.execute_script("return document.documentElement.clientWidth")
            assert sw <= cw, f"Overflow at {vp['name']}: {sw} > {cw}"
        log_step(15, total_steps, "Responsive Audit (8/8 Viewports, 0 Overflow)")

    finally:
        driver.quit()

    print("\n>>> ALL 15 SELENIUM VISIBLE TESTS PASSED <<<\n", flush=True)


if __name__ == "__main__":
    run_playwright_suite()
    run_selenium_suite()
