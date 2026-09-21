import sys
import time
from typing import Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5173"


class Phase14SeleniumSuite:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.driver = None
        self.test_results: Dict[str, str] = {}

    def setup(self):
        options = Options()
        options.binary_location = CHROME_PATH
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1440,900")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(5)

    def teardown(self):
        if self.driver:
            self.driver.quit()

    # =========================================================================
    # 1. AUTHENTICATION & WORKSPACE CONTEXT
    # =========================================================================
    def test_workspace_context_and_badge(self):
        print("\n--- [SELENIUM] 1. Testing Workspace Context & Navigation Badge ---")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "top-nav-workspace-badge"))
            )
            badge = self.driver.find_element(By.ID, "top-nav-workspace-badge")
            assert badge.is_displayed()
            badge_text = badge.text
            assert "workspace" in badge_text.lower(), f"Unexpected workspace badge: {badge_text}"
            print(f"  ✓ Workspace badge verified: '{badge_text}'")
            self.test_results["workspace_context"] = "PASS"
        except Exception as e:
            self.test_results["workspace_context"] = f"FAIL: {e}"
            raise

    # =========================================================================
    # 2. ACTUAL ROLE DISPLAY & ZERO SELF-SERVICE ROLE SWITCHER
    # =========================================================================
    def test_user_menu_and_authoritative_role(self):
        print("\n--- [SELENIUM] 2. Testing Production User Menu & Authoritative Role ---")
        try:
            self.driver.get(self.base_url)
            user_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "user-profile-menu-button"))
            )
            user_btn.click()
            time.sleep(0.3)

            dropdown = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "user-profile-dropdown"))
            )
            assert dropdown.is_displayed()

            name_elem = self.driver.find_element(By.ID, "user-profile-name")
            email_elem = self.driver.find_element(By.ID, "user-profile-email")
            ws_elem = self.driver.find_element(By.ID, "user-profile-workspace")
            role_elem = self.driver.find_element(By.ID, "user-profile-role")

            assert name_elem.is_displayed()
            assert email_elem.is_displayed()
            assert "Workspace:" in ws_elem.text
            assert "Role:" in role_elem.text
            print(f"  ✓ User: {name_elem.text}, Email: {email_elem.text}")
            print(f"  ✓ Workspace context: {ws_elem.text}")
            print(f"  ✓ Authoritative role: {role_elem.text}")

            # Verify no role switcher buttons
            buttons = dropdown.find_elements(By.XPATH, ".//button[contains(., 'Switch to')]")
            assert len(buttons) == 0, "No client-side role switcher should exist in production"
            print("  ✓ Zero self-service role switcher buttons present")

            self.test_results["authoritative_role_display"] = "PASS"
        except Exception as e:
            self.test_results["authoritative_role_display"] = f"FAIL: {e}"
            raise

    # =========================================================================
    # 3. NOTIFICATION DRAWER & MUTUAL EXCLUSIVITY
    # =========================================================================
    def test_popover_mutual_exclusivity(self):
        print("\n--- [SELENIUM] 3. Testing Popover Mutual Exclusivity & Dismissal ---")
        try:
            self.driver.get(self.base_url)
            bell_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "top-nav-bell-btn"))
            )
            user_btn = self.driver.find_element(By.ID, "user-profile-menu-button")

            # 1. Open notifications
            bell_btn.click()
            time.sleep(0.3)
            notif_panel = self.driver.find_element(By.ID, "notifications-panel")
            assert notif_panel.is_displayed()

            # 2. Click user profile -> notifications closes, user menu opens
            user_btn.click()
            time.sleep(0.3)
            user_dropdown = self.driver.find_element(By.ID, "user-profile-dropdown")
            assert user_dropdown.is_displayed()
            notifs = self.driver.find_elements(By.ID, "notifications-panel")
            assert len(notifs) == 0 or not notifs[0].is_displayed(), "Notifications must be closed"
            print("  ✓ Mutual exclusivity: opening user menu closes notification panel")

            # 3. Outside click
            body = self.driver.find_element(By.TAG_NAME, "header")
            webdriver.ActionChains(self.driver).move_to_element_with_offset(body, 20, 20).click().perform()
            time.sleep(0.3)
            user_menus = self.driver.find_elements(By.ID, "user-profile-dropdown")
            assert len(user_menus) == 0 or not user_menus[0].is_displayed(), "User menu must close on outside click"
            print("  ✓ Outside click closes user menu")

            self.test_results["popover_mutual_exclusivity"] = "PASS"
        except Exception as e:
            self.test_results["popover_mutual_exclusivity"] = f"FAIL: {e}"
            raise

    def login_admin(self):
        try:
            import urllib.request, json
            login_data = json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode()
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_data, headers={"Content-Type": "application/json"})
            res = urllib.request.urlopen(req)
            login_resp = json.loads(res.read())
            admin_token = login_resp["access_token"]
            admin_user = login_resp["user"]

            self.driver.get(f"{self.base_url}/")
            self.driver.execute_script(f"""
                localStorage.setItem('devforge_auth_token', '{admin_token}');
                localStorage.setItem('devforge_auth_user', JSON.stringify({json.dumps(admin_user)}));
                localStorage.setItem('devforge_active_workspace_id', '1');
            """)
        except Exception as e:
            print(f"  Note on login_admin: {e}")

    # =========================================================================
    # 4. SETTINGS MEMBERS MANAGEMENT
    # =========================================================================
    def test_settings_member_management(self):
        print("\n--- [SELENIUM] 4. Testing Settings Members Management ---")
        try:
            self.login_admin()
            self.driver.get(f"{self.base_url}/settings?tab=members")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "settings-tab-members"))
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='member-row']"))
            )
            time.sleep(0.5)

            # Check rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='member-row']")
            assert len(rows) >= 1, f"Expected member rows, found {len(rows)}"
            print(f"  ✓ {len(rows)} members rendered in table")

            # Check Add Member button
            add_btns = self.driver.find_elements(By.ID, "add-member-button")
            if add_btns and add_btns[0].is_displayed():
                add_btns[0].click()
                time.sleep(0.3)
                modal = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "add-member-email-input"))
                )
                assert modal.is_displayed()
                cancel_btn = self.driver.find_element(By.ID, "add-member-cancel-button")
                cancel_btn.click()
                time.sleep(0.2)
                print("  ✓ Add Member modal open & cancel verified")

            self.test_results["settings_members_management"] = "PASS"
        except Exception as e:
            self.test_results["settings_members_management"] = f"FAIL: {e}"
            raise

    # =========================================================================
    # 5. RESPONSIVE BEHAVIOR & OVERFLOW
    # =========================================================================
    def test_responsive_layout(self):
        print("\n--- [SELENIUM] 5. Testing Responsive Layout & Zero Overflow ---")
        try:
            viewports = [(1440, 900), (768, 1024), (375, 667)]
            for w, h in viewports:
                self.driver.set_window_size(w, h)
                for route in ["/", "/applications", "/settings?tab=members"]:
                    self.driver.get(f"{self.base_url}{route}")
                    time.sleep(0.3)
                    has_overflow = self.driver.execute_script(
                        "return document.documentElement.scrollWidth > document.documentElement.clientWidth;"
                    )
                    assert not has_overflow, f"Horizontal overflow at {w}x{h} on {route}"
                print(f"  ✓ {w}x{h} passed zero horizontal overflow")

            self.test_results["responsive_layout"] = "PASS"
        except Exception as e:
            self.test_results["responsive_layout"] = f"FAIL: {e}"
            raise

    def run_all(self) -> bool:
        self.setup()
        try:
            self.test_workspace_context_and_badge()
            self.test_user_menu_and_authoritative_role()
            self.test_popover_mutual_exclusivity()
            self.test_settings_member_management()
            self.test_responsive_layout()

            print("\n=======================================================")
            print("SELENIUM PHASE 14 TEST SUITE SUMMARY")
            print("=======================================================")
            all_passed = True
            for test_name, result in self.test_results.items():
                print(f"  {test_name}: {result}")
                if "FAIL" in result:
                    all_passed = False
            return all_passed
        finally:
            self.teardown()


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    suite = Phase14SeleniumSuite(base_url=target_url)
    success = suite.run_all()
    sys.exit(0 if success else 1)
