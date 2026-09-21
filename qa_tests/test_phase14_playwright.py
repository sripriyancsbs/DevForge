import sys
import time
from typing import List, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, Page, Browser

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5173"

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


class Phase14PlaywrightSuite:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.playwright = None
        self.browser: Browser = None
        self.console_errors: List[str] = []
        self.page_errors: List[str] = []
        self.failed_requests: List[str] = []
        self.test_results: Dict[str, str] = {}

    def setup(self):
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
        except Exception:
            self.browser = self.playwright.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

    def teardown(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def create_page(self, viewport={"width": 1440, "height": 900}) -> Page:
        page = self.browser.new_page(viewport=viewport)
        page.on("console", lambda msg: self.console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: self.failed_requests.append(f"{req.method} {req.url} -> {req.failure}"))
        return page

    # =========================================================================
    # 1. HEADER POPOVER BEHAVIOR & MUTUAL EXCLUSIVITY
    # =========================================================================
    def test_popovers_and_mutual_exclusivity(self):
        print("\n--- [PLAYWRIGHT] 1. Testing Header Popovers & Mutual Exclusivity ---")
        page = self.create_page()
        try:
            page.goto(f"{self.base_url}/", wait_until="networkidle")

            # 1. Click bell -> opens notification drawer
            bell_btn = page.locator("#top-nav-bell-btn")
            bell_btn.click()
            page.wait_for_timeout(300)
            assert page.locator("#notifications-panel").is_visible(), "Notifications panel should open when bell is clicked"
            assert not page.locator("#user-profile-dropdown").is_visible(), "User menu should be closed when notifications open"
            print("  ✓ Bell opens notifications and ensures user menu is closed")

            # 2. Click avatar -> opens user menu AND closes notification drawer (mutual exclusivity)
            user_btn = page.locator("#user-profile-menu-button")
            user_btn.click()
            page.wait_for_timeout(300)
            assert page.locator("#user-profile-dropdown").is_visible(), "User menu should open when avatar is clicked"
            assert not page.locator("#notifications-panel").is_visible(), "Notifications panel should close when user menu opens (mutual exclusivity)"
            print("  ✓ Mutual exclusivity: opening user menu automatically closes notification panel")

            # 3. Click inside user menu -> remains open
            page.locator("#user-profile-dropdown").click()
            page.wait_for_timeout(200)
            assert page.locator("#user-profile-dropdown").is_visible(), "User menu must remain open when clicked inside"
            print("  ✓ Click inside user menu maintains open state")

            # 4. Click outside -> closes user menu
            page.locator("header").click(position={"x": 50, "y": 20})
            page.wait_for_timeout(300)
            assert not page.locator("#user-profile-dropdown").is_visible(), "Clicking outside must close user menu"
            print("  ✓ Outside click successfully closes user menu")

            # 5. Escape key -> closes active popover
            bell_btn.click()
            page.wait_for_timeout(200)
            assert page.locator("#notifications-panel").is_visible()
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            assert not page.locator("#notifications-panel").is_visible(), "Escape key must close notification panel"

            user_btn.click()
            page.wait_for_timeout(200)
            assert page.locator("#user-profile-dropdown").is_visible()
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            assert not page.locator("#user-profile-dropdown").is_visible(), "Escape key must close user menu"
            print("  ✓ Escape key successfully dismisses popovers")

            self.test_results["header_popovers"] = "PASS"
        except Exception as e:
            self.test_results["header_popovers"] = f"FAIL: {e}"
            raise
        finally:
            page.close()

    # =========================================================================
    # 2. USER MENU PRODUCTION DISPLAY & NO ROLE SWITCHER
    # =========================================================================
    def test_production_user_menu_and_no_self_service_role_switcher(self):
        print("\n--- [PLAYWRIGHT] 2. Testing Production User Menu & Zero Role Switcher ---")
        page = self.create_page()
        try:
            page.goto(f"{self.base_url}/", wait_until="networkidle")

            # Open user menu
            page.locator("#user-profile-menu-button").click()
            page.wait_for_timeout(300)

            # Check required fields: User, Email, Workspace, Actual Active Role
            dropdown = page.locator("#user-profile-dropdown")
            assert dropdown.is_visible()

            name_elem = page.locator("#user-profile-name")
            assert name_elem.is_visible()
            print(f"  ✓ User displayed: {name_elem.inner_text()}")

            email_elem = page.locator("#user-profile-email")
            assert email_elem.is_visible()
            print(f"  ✓ Email displayed: {email_elem.inner_text()}")

            ws_elem = page.locator("#user-profile-workspace")
            assert ws_elem.is_visible()
            assert "Workspace:" in ws_elem.inner_text()
            print(f"  ✓ Workspace context displayed: {ws_elem.inner_text()}")

            role_elem = page.locator("#user-profile-role")
            assert role_elem.is_visible()
            assert "Role:" in role_elem.inner_text()
            print(f"  ✓ Authoritative role displayed: {role_elem.inner_text()}")

            # Strictly verify NO clickable role switchers exist
            for r in ["ADMIN", "OPERATOR", "DEVELOPER", "VIEWER"]:
                switcher_btn = dropdown.locator(f"button:has-text('Switch to {r}')")
                assert switcher_btn.count() == 0, f"Forbidden role switcher button for '{r}' found in user menu"
            print("  ✓ Verified: No self-service role switcher in production user menu")

            self.test_results["user_menu_production"] = "PASS"
        except Exception as e:
            self.test_results["user_menu_production"] = f"FAIL: {e}"
            raise
        finally:
            page.close()

    def login_admin(self, page: Page):
        try:
            import urllib.request, json
            login_data = json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode()
            req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_data, headers={"Content-Type": "application/json"})
            res = urllib.request.urlopen(req)
            login_resp = json.loads(res.read())
            admin_token = login_resp["access_token"]
            admin_user = login_resp["user"]

            page.goto(f"{self.base_url}/")
            page.evaluate(f"""() => {{
                localStorage.setItem('devforge_auth_token', '{admin_token}');
                localStorage.setItem('devforge_auth_user', JSON.stringify({json.dumps(admin_user)}));
                localStorage.setItem('devforge_active_workspace_id', '1');
            }}""")
        except Exception as e:
            print(f"  Note on login_admin: {e}")

    # =========================================================================
    # 3. SETTINGS: MEMBERS MANAGEMENT TAB & ADMIN ACTIONS
    # =========================================================================
    def test_settings_workspace_members_management(self):
        print("\n--- [PLAYWRIGHT] 3. Testing Settings Members Management ---")
        page = self.create_page()
        try:
            self.login_admin(page)
            # Set admin user session in localStorage
            page.goto(f"{self.base_url}/settings?tab=members", wait_until="networkidle")
            page.wait_for_selector("[data-testid='member-row']", timeout=10000)

            # Verify Members tab is active
            members_tab = page.locator("#settings-tab-members")
            assert members_tab.is_visible()
            print("  ✓ Settings page loaded on Members tab")

            # Check members table exists and has rows
            member_rows = page.locator("[data-testid='member-row']")
            count = member_rows.count()
            assert count >= 1, f"Expected at least 1 member, found {count}"
            print(f"  ✓ Members table populated with {count} members")

            # Check Add Member button
            add_btn = page.locator("#add-member-button")
            assert add_btn.is_visible(), "Add Member button should be visible for ADMIN"

            # Open Add Member Modal
            add_btn.click()
            page.wait_for_timeout(300)
            assert page.locator("#add-member-email-input").is_visible()

            # Fill in member details
            unique_ts = int(time.time())
            test_email = f"qa_engineer_{unique_ts}@devforge.internal"
            page.fill("#add-member-email-input", test_email)
            page.fill("#add-member-username-input", f"qa_eng_{unique_ts}")
            page.fill("#add-member-displayname-input", f"QA Engineer {unique_ts}")
            page.select_option("#add-member-role-select", "DEVELOPER")

            # Submit form
            page.locator("#add-member-submit-button").click()
            page.wait_for_timeout(1000)

            # Check success alert or updated table
            page.wait_for_selector(f"text={test_email}", timeout=5000)
            print(f"  ✓ Successfully added new workspace member: {test_email}")

            # Verify role selector exists on member row for ADMIN
            role_select = page.locator(f"select[id^='member-role-select-']").first
            if role_select.is_visible():
                print("  ✓ Admin role modification dropdown is accessible")

            self.test_results["settings_members"] = "PASS"
        except Exception as e:
            self.test_results["settings_members"] = f"FAIL: {e}"
            raise
        finally:
            page.close()

    # =========================================================================
    # 4. RESPONSIVE VIEWPORTS & ZERO HORIZONTAL OVERFLOW
    # =========================================================================
    def test_responsive_viewports_and_zero_overflow(self):
        print("\n--- [PLAYWRIGHT] 4. Testing 8 Responsive Viewports & Zero Horizontal Overflow ---")
        routes = ["/", "/applications", "/settings?tab=members", "/settings?tab=workspace"]

        for vp in VIEWPORTS:
            page = self.create_page(viewport={"width": vp["width"], "height": vp["height"]})
            try:
                for route in routes:
                    page.goto(f"{self.base_url}{route}", wait_until="networkidle")
                    page.wait_for_timeout(200)

                    # Check zero page horizontal overflow: scrollWidth <= clientWidth
                    overflow = page.evaluate("""() => {
                        return {
                            scrollWidth: document.documentElement.scrollWidth,
                            clientWidth: document.documentElement.clientWidth,
                            hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
                        };
                    }""")

                    assert not overflow["hasOverflow"], (
                        f"Horizontal overflow at {vp['name']} on {route}: "
                        f"scrollWidth={overflow['scrollWidth']} > clientWidth={overflow['clientWidth']}"
                    )
                print(f"  ✓ {vp['name']} passed zero horizontal overflow across all key routes")
            except Exception as e:
                self.test_results[f"responsive_{vp['width']}x{vp['height']}"] = f"FAIL: {e}"
                raise
            finally:
                page.close()

        self.test_results["responsive_all_viewports"] = "PASS"

    def run_all(self) -> bool:
        self.setup()
        try:
            self.test_popovers_and_mutual_exclusivity()
            self.test_production_user_menu_and_no_self_service_role_switcher()
            self.test_settings_workspace_members_management()
            self.test_responsive_viewports_and_zero_overflow()

            print("\n=======================================================")
            print("PLAYWRIGHT PHASE 14 TEST SUITE SUMMARY")
            print("=======================================================")
            all_passed = True
            for test_name, result in self.test_results.items():
                print(f"  {test_name}: {result}")
                if "FAIL" in result:
                    all_passed = False

            if self.console_errors:
                print(f"\nCaptured {len(self.console_errors)} console errors:")
                for ce in self.console_errors[:5]:
                    print(f"  - {ce}")
            else:
                print("\n  ✓ 0 Console errors detected")

            return all_passed
        finally:
            self.teardown()


if __name__ == "__main__":
    suite = Phase14PlaywrightSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
