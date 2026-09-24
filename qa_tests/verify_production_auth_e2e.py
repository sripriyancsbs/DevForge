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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.environ.get("DEVFORGE_TEST_URL", "https://frontend-two-self-3343htd1ck.vercel.app").rstrip("/")

VIEWPORTS = [
    {"width": 1920, "height": 1080, "name": "1920x1080 (Desktop FHD)"},
    {"width": 1440, "height": 900, "name": "1440x900 (Desktop Laptop)"},
    {"width": 1280, "height": 800, "name": "1280x800 (Laptop Standard)"},
    {"width": 1024, "height": 768, "name": "1024x768 (Tablet Landscape)"},
    {"width": 820, "height": 1180, "name": "820x1180 (iPad Air)"},
    {"width": 768, "height": 1024, "name": "768x1024 (Tablet Portrait)"},
    {"width": 414, "height": 896, "name": "414x896 (iPhone XR/11)"},
    {"width": 390, "height": 844, "name": "390x844 (iPhone 12/13/14)"},
    {"width": 375, "height": 667, "name": "375x667 (Mobile Small)"}
]

def log_step(step_num: int, total: int, description: str, status: str = "PASS"):
    padded_desc = description.ljust(52, ".")
    print(f"[{step_num:02d}/{total:02d}] {padded_desc} {status}", flush=True)

def reset_backend_rate_limits():
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://corp-social-anthropology-wishes.trycloudflare.com/api/v1/auth/reset-rate-limit",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def run_playwright_suite():
    reset_backend_rate_limits()
    total_steps = 25
    print("\n" + "=" * 80)
    print("PLAYWRIGHT — VISIBLE PRODUCTION E2E AUTH & RBAC SUITE (HEADED WINDOW)")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80 + "\n", flush=True)

    ts = int(time.time())
    dev_user = f"dev_{ts}"
    dev_email = f"{dev_user}@devforge.com"
    dev_pass = "DevPassword2026!"

    pub_user = f"pub_{ts}"
    pub_email = f"{pub_user}@devforge.com"
    pub_pass = "PubPassword2026!"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=["--start-maximized"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900}, no_viewport=True)
        page = context.new_page()

        try:
            # STEP 01: Unauthenticated Initial State
            page.goto(f"{BASE_URL}/signin", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            # Verify no Active Role: VIEWER is visible
            body_text = page.locator("body").inner_text()
            assert "Active Role: VIEWER" not in body_text, "Found 'Active Role: VIEWER' in unauthenticated view!"
            # TopNav must show Sign In / Sign Up buttons
            assert page.locator("#top-nav-signin-btn").is_visible() or page.locator("button:has-text('Sign In')").is_visible()
            log_step(1, total_steps, "Unauthenticated /signin rendered with NO active role")

            # STEP 02: Protected Route Guard
            page.goto(f"{BASE_URL}/applications", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            assert "/signin" in page.url or page.locator("#signin-submit-btn").is_visible(), "Failed to redirect unauthenticated user to /signin"
            log_step(2, total_steps, "Protected route /applications guards unauthenticated user")

            # STEP 03: Bootstrap Admin Sign In
            reset_backend_rate_limits()
            page.fill("#signin-email-input", "admin@devforge.com")
            page.fill("#signin-password-input", "pass123")
            page.click("#signin-submit-btn")
            page.wait_for_url(lambda u: "/signin" not in u, timeout=15000)
            page.wait_for_timeout(1200)
            log_step(3, total_steps, "Bootstrap admin (admin@devforge.com) sign in succeeded")

            # STEP 04: Verify Authoritative Role ADMIN in User Menu
            menu_btn = page.locator("#user-profile-menu-button")
            menu_btn.wait_for(state="visible", timeout=10000)
            assert "ADMIN" in menu_btn.inner_text(), f"Expected role ADMIN in TopNav, got: {menu_btn.inner_text()}"
            menu_btn.click()
            page.wait_for_selector("#user-profile-dropdown", state="visible")
            assert "ADMIN" in page.locator("#user-profile-role").inner_text()
            page.click("#user-profile-menu-button") # close menu
            log_step(4, total_steps, "Authoritative role ADMIN verified in topnav and user profile")

            # STEP 05: Navigate to Platform Settings -> Workspace Members
            page.goto(f"{BASE_URL}/settings?tab=members", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            assert page.locator("#settings-tab-members").is_visible()
            log_step(5, total_steps, "Navigated to Settings -> Workspace Members")

            # STEP 06: Verify Members Table
            page.wait_for_selector("table", state="visible", timeout=10000)
            table_text = page.locator("table").inner_text()
            assert "admin@devforge.com" in table_text or "Platform Administrator" in table_text or "admin" in table_text
            log_step(6, total_steps, "Members table rendered with bootstrap admin")

            # STEP 07: Open Create User / Add Member Modal
            add_btn = page.locator("#add-member-button")
            add_btn.wait_for(state="visible", timeout=5000)
            add_btn.click()
            page.wait_for_selector("#add-member-email-input", state="visible")
            log_step(7, total_steps, "Add Member modal opened")

            # STEP 08: Fill User Creation Form
            page.fill("#add-member-name-input", "Test Developer")
            page.fill("#add-member-email-input", dev_email)
            page.fill("#add-member-password-input", dev_pass)
            page.fill("#add-member-confirmpassword-input", dev_pass)
            page.select_option("#add-member-role-select", "DEVELOPER")
            log_step(8, total_steps, "Form filled with Name, Email, Password, Confirm Password, Role")

            # STEP 09: Submit User Creation
            page.click("#add-member-submit-button")
            page.wait_for_selector(f"tr:has-text('{dev_email}')", state="visible", timeout=15000)
            created_row = page.locator(f"tr:has-text('{dev_email}')")
            assert "DEVELOPER" in created_row.inner_text()
            log_step(9, total_steps, f"New user created and displayed with role DEVELOPER ({dev_email})")

            # STEP 10: Admin Logout -> Verify Clean Signed-Out State
            menu_btn = page.locator("#user-profile-menu-button")
            menu_btn.click()
            page.wait_for_selector("#user-logout-button", state="visible")
            page.click("#user-logout-button")
            page.wait_for_timeout(1500)
            # URL must be /signin
            assert "/signin" in page.url, f"Expected /signin after logout, got: {page.url}"
            # Verify body does NOT contain "Active Role: VIEWER"
            body_logout = page.locator("body").inner_text()
            assert "Active Role: VIEWER" not in body_logout, "Error: 'Active Role: VIEWER' present after logout!"
            assert page.locator("#top-nav-signin-btn").is_visible() or page.locator("button:has-text('Sign In')").is_visible()
            log_step(10, total_steps, "Logout successfully invalidated session, NO active role shown")

            # STEP 11: Sign In with Newly Created Developer
            reset_backend_rate_limits()
            page.fill("#signin-email-input", dev_email)
            page.fill("#signin-password-input", dev_pass)
            page.click("#signin-submit-btn")
            page.wait_for_url(lambda u: "/signin" not in u, timeout=15000)
            page.wait_for_timeout(1000)
            log_step(11, total_steps, f"Signed in with created developer account ({dev_email})")

            # STEP 12: Verify Developer Authoritative Role
            menu_btn = page.locator("#user-profile-menu-button")
            menu_btn.wait_for(state="visible", timeout=10000)
            assert "DEVELOPER" in menu_btn.inner_text(), f"Expected role DEVELOPER in TopNav, got: {menu_btn.inner_text()}"
            menu_btn.click()
            assert "DEVELOPER" in page.locator("#user-profile-role").inner_text()
            page.click("#user-profile-menu-button")
            log_step(12, total_steps, "Verified authoritative role DEVELOPER for new user")

            # STEP 13: Verify Developer RBAC Permissions
            page.goto(f"{BASE_URL}/settings?tab=members", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            # Add Member button should NOT be visible for DEVELOPER
            assert not page.locator("#add-member-button").is_visible(), "DEVELOPER should not see Add Member button!"
            assert page.locator("text=Read-only view").is_visible(), "Expected Read-only notice for non-admin"
            log_step(13, total_steps, "Developer RBAC verified (settings members is read-only)")

            # STEP 14: Logout Developer
            menu_btn = page.locator("#user-profile-menu-button")
            menu_btn.click()
            page.click("#user-logout-button")
            page.wait_for_timeout(1200)
            assert "/signin" in page.url
            log_step(14, total_steps, "Developer signed out cleanly")

            # STEP 15: Navigate to Public Sign Up
            page.goto(f"{BASE_URL}/signup", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(800)
            assert page.locator("#signup-name-input").is_visible()
            log_step(15, total_steps, "Navigated to public /signup registration screen")

            # STEP 16: Fill Public Sign Up Form
            page.fill("#signup-name-input", "Public Visitor")
            page.fill("#signup-email-input", pub_email)
            page.fill("#signup-password-input", pub_pass)
            page.fill("#signup-confirm-password-input", pub_pass)
            log_step(16, total_steps, "Public registration form filled")

            # STEP 17: Submit Public Sign Up -> Verify Safe Default VIEWER Role
            page.click("#signup-submit-btn")
            page.wait_for_url(lambda u: "/signup" not in u, timeout=15000)
            page.wait_for_timeout(1200)
            menu_btn = page.locator("#user-profile-menu-button")
            menu_btn.wait_for(state="visible", timeout=10000)
            assert "VIEWER" in menu_btn.inner_text(), f"Expected safe default role VIEWER, got: {menu_btn.inner_text()}"
            log_step(17, total_steps, "Public sign up completed with authoritative safe default VIEWER role")

            # STEP 18: Logout Viewer
            menu_btn.click()
            page.click("#user-logout-button")
            page.wait_for_timeout(1200)
            log_step(18, total_steps, "Public viewer signed out cleanly")

            # STEP 19: Sign In back as Administrator
            reset_backend_rate_limits()
            page.fill("#signin-email-input", "admin@devforge.com")
            page.fill("#signin-password-input", "pass123")
            page.click("#signin-submit-btn")
            page.wait_for_url(lambda u: "/signin" not in u, timeout=15000)
            page.wait_for_timeout(1000)
            log_step(19, total_steps, "Admin re-authenticated")

            # STEP 20: Navigate to Settings -> Members
            page.goto(f"{BASE_URL}/settings?tab=members", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            log_step(20, total_steps, "Navigated back to workspace members")

            # STEP 21: Admin Updates Member Role (Change to OPERATOR)
            dev_row = page.locator(f"tr:has-text('{dev_email}')")
            dev_row.wait_for(state="visible", timeout=10000)
            role_select = dev_row.locator("select")
            role_select.select_option("OPERATOR")
            page.wait_for_timeout(1500)
            page.wait_for_selector("#settings-action-success", state="visible", timeout=8000)
            log_step(21, total_steps, f"Admin updated role for {dev_email} to OPERATOR")

            # STEP 22: Admin Disables Member
            page.on("dialog", lambda dialog: dialog.accept())
            disable_btn = dev_row.locator("button:has-text('Disable')")
            disable_btn.click()
            page.wait_for_timeout(1500)
            # Verify row indicates disabled
            updated_dev_row = page.locator(f"tr:has-text('{dev_email}')")
            assert "disabled" in updated_dev_row.inner_text().lower()
            log_step(22, total_steps, f"Admin disabled member {dev_email}")

            # STEP 23: Admin Deletes Member
            delete_btn = updated_dev_row.locator("button:has-text('Delete')")
            delete_btn.click()
            page.wait_for_timeout(2000)
            # User should no longer appear in the table
            assert not page.locator(f"tr:has-text('{dev_email}')").is_visible()
            log_step(23, total_steps, f"Admin deleted member {dev_email}")

            # STEP 24: Final Admin Protection Check
            # In the table, the admin row has NO role dropdown (cannot self-demote) and NO disable/delete button
            admin_row = page.locator("tr:has-text('admin@devforge.com')")
            assert not admin_row.locator("select").is_visible(), "Admin should not be able to self-demote role!"
            assert not admin_row.locator("button:has-text('Delete')").is_visible(), "Admin should not have delete button for self!"
            log_step(24, total_steps, "Final remaining admin protection verified")

            # STEP 25: 8-Viewport Responsive Audit (Zero Horizontal Overflow)
            all_viewports_passed = True
            for vp in VIEWPORTS:
                page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                page.wait_for_timeout(300)
                is_overflow = page.evaluate("""() => {
                    return document.documentElement.scrollWidth > window.innerWidth;
                }""")
                if is_overflow:
                    all_viewports_passed = False
                    print(f"   [OVERFLOW DETECTED] at viewport {vp['name']}")
                else:
                    print(f"   [0-OVERFLOW PASS] Viewport {vp['name']}")
            assert all_viewports_passed, "Horizontal overflow detected in responsive audit!"
            log_step(25, total_steps, "Responsive viewport audit (9 viewports) passed with 0 horizontal overflow")

            print("\n" + "=" * 80)
            print("ALL 25 PLAYWRIGHT PRODUCTION E2E TESTS PASSED SUCCESSFULLY!")
            print("=" * 80 + "\n", flush=True)

        finally:
            context.close()
            browser.close()


def run_selenium_suite():
    reset_backend_rate_limits()
    total_steps = 15
    print("\n" + "=" * 80)
    print("SELENIUM — VISIBLE CHROME SUITE (PHYSICAL WINDOW ON DESKTOP)")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80 + "\n", flush=True)

    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # STEP 01: Unauthenticated View
        driver.get(f"{BASE_URL}/signin")
        time.sleep(1.5)
        body = driver.find_element(By.TAG_NAME, "body").text
        assert "Active Role: VIEWER" not in body, "Found 'Active Role: VIEWER' in unauthenticated page!"
        log_step(1, total_steps, "Selenium loaded /signin with NO active role")

        # STEP 02: Admin Login
        email_in = wait.until(EC.visibility_of_element_located((By.ID, "signin-email-input")))
        pass_in = driver.find_element(By.ID, "signin-password-input")
        submit_btn = driver.find_element(By.ID, "auth-form-submit-button")
        email_in.send_keys("admin@devforge.com")
        pass_in.send_keys("pass123")
        submit_btn.click()
        time.sleep(2)
        log_step(2, total_steps, "Selenium submitted admin credentials")

        # STEP 03: Verify Authoritative Role ADMIN
        profile_btn = wait.until(EC.visibility_of_element_located((By.ID, "user-profile-menu-button")))
        assert "ADMIN" in profile_btn.text, f"Expected role ADMIN in TopNav, got: {profile_btn.text}"
        log_step(3, total_steps, "Selenium verified TopNav authoritative role ADMIN")

        # STEP 04: User Menu Profile Verification
        profile_btn.click()
        time.sleep(0.5)
        role_el = wait.until(EC.visibility_of_element_located((By.ID, "user-profile-role")))
        assert "ADMIN" in role_el.text
        log_step(4, total_steps, "Selenium verified User Profile dropdown authoritative role")

        # STEP 05: Navigate to Platform Settings
        driver.get(f"{BASE_URL}/settings?tab=members")
        time.sleep(1.5)
        members_tab = wait.until(EC.visibility_of_element_located((By.ID, "settings-tab-members")))
        assert members_tab.is_displayed()
        log_step(5, total_steps, "Selenium opened Settings -> Members")

        # STEP 06: Verify Members Table
        table = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "table")))
        assert "admin@devforge.com" in table.text or "Platform Administrator" in table.text
        log_step(6, total_steps, "Selenium verified table contents with bootstrap admin")

        # STEP 07: Open Add Member Modal
        add_btn = wait.until(EC.element_to_be_clickable((By.ID, "add-member-button")))
        add_btn.click()
        time.sleep(0.5)
        email_field = wait.until(EC.visibility_of_element_located((By.ID, "add-member-email-input")))
        log_step(7, total_steps, "Selenium opened Add Member modal")

        # STEP 08: Create Member
        ts = int(time.time())
        sel_email = f"sel_{ts}@devforge.com"
        name_field = driver.find_element(By.ID, "add-member-name-input")
        pwd_field = driver.find_element(By.ID, "add-member-password-input")
        cpwd_field = driver.find_element(By.ID, "add-member-confirmpassword-input")
        role_select = Select(driver.find_element(By.ID, "add-member-role-select"))
        modal_submit = driver.find_element(By.ID, "add-member-submit-button")

        name_field.send_keys("Selenium User")
        email_field.send_keys(sel_email)
        pwd_field.send_keys("SeleniumPassword2026!")
        cpwd_field.send_keys("SeleniumPassword2026!")
        role_select.select_by_value("DEVELOPER")
        modal_submit.click()
        time.sleep(2)
        log_step(8, total_steps, f"Selenium submitted user creation ({sel_email})")

        # STEP 09: Verify User Created in Table
        table = wait.until(EC.visibility_of_element_located((By.TAG_NAME, "table")))
        assert sel_email in table.text
        log_step(9, total_steps, "Selenium verified user in members table")

        # STEP 10: Role Change to OPERATOR
        row = driver.find_element(By.XPATH, f"//tr[contains(., '{sel_email}')]")
        row_select = Select(row.find_element(By.TAG_NAME, "select"))
        row_select.select_by_value("OPERATOR")
        time.sleep(1.5)
        log_step(10, total_steps, "Selenium updated member role to OPERATOR")

        # STEP 11: Disable User
        row = driver.find_element(By.XPATH, f"//tr[contains(., '{sel_email}')]")
        disable_btn = row.find_element(By.XPATH, ".//button[contains(text(), 'Disable')]")
        disable_btn.click()
        time.sleep(0.5)
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(1.5)
        log_step(11, total_steps, "Selenium accepted alert and disabled user")

        # STEP 12: Delete User
        row = driver.find_element(By.XPATH, f"//tr[contains(., '{sel_email}')]")
        delete_btn = row.find_element(By.XPATH, ".//button[contains(text(), 'Delete')]")
        delete_btn.click()
        time.sleep(0.5)
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(2)
        table_after = driver.find_element(By.TAG_NAME, "table").text
        assert sel_email not in table_after
        log_step(12, total_steps, "Selenium permanently deleted user")

        # STEP 13: Sign Out
        profile_btn = driver.find_element(By.ID, "user-profile-menu-button")
        profile_btn.click()
        time.sleep(0.5)
        logout_btn = wait.until(EC.element_to_be_clickable((By.ID, "user-logout-button")))
        logout_btn.click()
        time.sleep(1.5)
        log_step(13, total_steps, "Selenium signed out")

        # STEP 14: Verify Unauthenticated State
        assert "/signin" in driver.current_url
        body = driver.find_element(By.TAG_NAME, "body").text
        assert "Active Role: VIEWER" not in body, "Found 'Active Role: VIEWER' after logout in Selenium!"
        log_step(14, total_steps, "Selenium confirmed NO active role after logout")

        # STEP 15: Responsive Width Check
        widths = [1920, 1440, 1024, 768, 390]
        for w in widths:
            driver.set_window_size(w, 800)
            time.sleep(0.3)
            is_overflow = driver.execute_script("return document.documentElement.scrollWidth > window.innerWidth;")
            assert not is_overflow, f"Overflow detected at width {w}"
            print(f"   [0-OVERFLOW PASS] Width {w}px")
        log_step(15, total_steps, "Selenium responsive width checks passed")

        print("\n" + "=" * 80)
        print("ALL 15 SELENIUM PRODUCTION E2E TESTS PASSED SUCCESSFULLY!")
        print("=" * 80 + "\n", flush=True)

    finally:
        driver.quit()


if __name__ == "__main__":
    print(f"Executing End-to-End Verification against: {BASE_URL}")
    run_playwright_suite()
    run_selenium_suite()
    print("ALL TEST SUITES COMPLETED WITH 100% PASS RATE!")
