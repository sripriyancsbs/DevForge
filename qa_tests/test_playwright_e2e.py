import sys
import time
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, Page, Browser

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
API_URL = "http://127.0.0.1:8000"


class PlaywrightQASuite:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.console_errors: List[str] = []
        self.page_errors: List[str] = []
        self.failed_requests: List[str] = []
        self.test_results: Dict[str, str] = {}

    def setup(self):
        self.playwright = sync_playwright().start()
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

    def create_monitored_page(self, viewport={"width": 1440, "height": 900}) -> Page:
        page = self.browser.new_page(viewport=viewport)
        page.on("console", lambda msg: self.console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: self.failed_requests.append(f"{req.method} {req.url} -> {req.failure}"))
        return page

    # =========================================================================
    # 1. NAVIGATION & CORE VIEWS
    # =========================================================================
    def test_navigation_and_views(self):
        print("\n--- [PLAYWRIGHT] Testing Navigation & Core Views ---")
        page = self.create_monitored_page()
        try:
            # 1. Overview Page
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            assert "DevForge" in page.title(), f"Overview title mismatch: {page.title()}"
            page.locator("h1:has-text('Platform Overview')").wait_for(state="visible", timeout=10000)
            print("  ✓ Overview page loaded")

            # 2. Applications Page
            page.locator("aside button:has-text('Applications')").first.click()
            page.wait_for_timeout(300)
            assert page.locator("h1:has-text('Applications')").is_visible() or page.locator("input[placeholder*='Filter by application']").is_visible()
            print("  ✓ Applications inventory page loaded")

            # 3. Deployments Page
            page.locator("aside button:has-text('Deployments')").first.click()
            page.locator("h1:has-text('Deployments')").wait_for(state="visible", timeout=5000)
            print("  ✓ Deployments page loaded")

            # 4. Environments Page
            page.locator("aside button:has-text('Environments')").first.click()
            page.locator("h1:has-text('Environments')").wait_for(state="visible", timeout=5000)
            print("  ✓ Environments page loaded")

            # 5. Infrastructure Page
            page.locator("aside button:has-text('Infrastructure')").first.click()
            page.locator("h1:has-text('Infrastructure')").wait_for(state="visible", timeout=5000)
            print("  ✓ Infrastructure page loaded")

            # 6. Monitoring Page
            page.locator("aside button:has-text('Monitoring')").first.click()
            page.locator("h1:has-text('Monitoring')").wait_for(state="visible", timeout=5000)
            print("  ✓ Monitoring page loaded")

            # 7. Activity Page
            page.locator("aside button:has-text('Activity')").first.click()
            page.locator("h1:has-text('Activity')").wait_for(state="visible", timeout=5000)
            print("  ✓ Activity audit trail page loaded")

            # 8. Settings Page
            page.locator("aside button:has-text('Settings')").first.click()
            page.locator("h1:has-text('Settings')").wait_for(state="visible", timeout=5000)
            print("  ✓ Settings page loaded")

            # 9. Command Palette (Search / Cmd+K)
            search_btn = page.locator("button:has-text('Search commands, services')").first
            if search_btn.is_visible():
                search_btn.click()
                page.wait_for_timeout(300)
                assert page.locator("input[placeholder*='Type a command or search']").is_visible(), "Command palette input did not open"
                page.keyboard.press("Escape")
                print("  ✓ Command palette open & Escape close")

            # 10. Notification Drawer
            bell_btn = page.locator("header button:has([class*='lucide-bell'])").first
            if bell_btn.is_visible():
                bell_btn.click()
                page.wait_for_timeout(300)
                bell_btn.click()
                print("  ✓ Notifications drawer toggle")

            # 11. Browser Back / Forward
            page.locator("aside button:has-text('Overview')").first.click()
            page.wait_for_load_state("networkidle")
            page.locator("aside button:has-text('Applications')").first.click()
            page.wait_for_load_state("networkidle")
            page.go_back()
            page.wait_for_load_state("networkidle")
            assert page.locator("h1:has-text('Platform Overview')").is_visible(), "Browser back failed"
            page.go_forward()
            page.wait_for_timeout(300)
            assert page.locator("h1:has-text('Applications')").is_visible(), "Browser forward failed"
            print("  ✓ Browser back and forward navigation")

            # 12. Page Refresh
            page.reload(wait_until="networkidle")
            page.locator("h1:has-text('Applications')").wait_for(state="visible", timeout=10000)
            print("  ✓ Page refresh verified")

            self.test_results["Navigation and Core Views"] = "PASS"
        except Exception as e:
            self.test_results["Navigation and Core Views"] = f"FAIL: {e}"
            print(f"  ❌ Navigation test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 2. CREATE APPLICATION (ALL 4 STARTER TEMPLATES & STEPPER)
    # =========================================================================
    def test_create_application_templates(self):
        run_suffix = int(time.time()) % 100000
        templates = [
            ("python-fastapi", f"qa-pw-py-{run_suffix}", "Python FastAPI"),
            ("react-vite", f"qa-pw-rc-{run_suffix}", "React + Vite"),
            ("go-microservice", f"qa-pw-go-{run_suffix}", "Go Microservice"),
            ("node-service", f"qa-pw-nd-{run_suffix}", "Node.js API")
        ]

        for tpl_id, app_name, tpl_display in templates:
            print(f"\n--- [PLAYWRIGHT] Provisioning Application: {app_name} ({tpl_display}) ---")
            page = self.create_monitored_page()
            try:
                page.goto(f"{BASE_URL}/create-application", wait_until="networkidle")

                # Verify wizard opened
                assert page.locator("h1:has-text('Create Application')").is_visible(), "Create Application header missing"

                # 1. Fill Name
                name_input = page.locator("input[placeholder*='order-processing-service']")
                name_input.fill(app_name)

                # Click Step 1 Next button
                next1 = page.locator("button:has-text('Next: Runtime & Template')").first
                assert next1.is_enabled(), "Next button disabled with valid name"
                next1.click()
                page.wait_for_timeout(300)

                # 2. Select Template
                tpl_card = page.locator(f"div:has-text('{tpl_display}')").last
                tpl_card.click()
                print(f"  ✓ Selected template: {tpl_display}")

                # Click Step 2 Next button
                page.locator("button:has-text('Next: Environment & Config')").first.click()
                page.wait_for_timeout(300)

                # 3. Submit Provisioning
                provision_btn = page.locator("button:has-text('Provision Application')")
                assert provision_btn.is_visible(), "Provision Application button not visible"
                provision_btn.click()
                print("  ✓ Provisioning submitted")

                # 4. Verify Stepper appears with Phase 3 steps
                stepper_header = page.locator("text=Provisioning Application").first
                stepper_header.wait_for(state="visible", timeout=10000)

                expected_steps = [
                    "Validate configuration",
                    "Generate project",
                    "Generate devforge.yaml",
                    "Generate CI workflow",
                    "Validate project",
                    "Create GitHub repository",
                    "Push repository",
                    "Ready"
                ]
                for step_name in expected_steps:
                    step_elem = page.locator(f"text={step_name}").first
                    assert step_elem.is_visible(), f"Stepper step '{step_name}' missing from UI"
                print("  ✓ All Phase 4 provisioning stepper stages verified in UI (including Generate CI workflow)")

                # 5. Wait for READY state (up to 60s for worker pickup, generation, GitHub repo creation & push)
                ready_indicator = page.locator("text=Application successfully generated and registered in PostgreSQL")
                ready_indicator.wait_for(state="visible", timeout=60000)
                print("  ✓ Provisioning reached READY state")

                # 6. Verify Success Screen GitHub Repository Card
                github_card = page.locator("text=GitHub Repository").first
                assert github_card.is_visible(), "GitHub Repository card not displayed on success screen"

                repo_link = page.locator("a:has-text('Open Repository')")
                assert repo_link.is_visible(), "'Open Repository' link missing on success screen"
                repo_href = repo_link.get_attribute("href")
                assert f"github.com/sripriyancsbs/{app_name}" in repo_href, f"Repository URL mismatch: {repo_href}"
                print(f"  ✓ GitHub Repository link verified: {repo_href}")

                # 7. Click 'Open Application' to view in Application Details
                page.locator("button:has-text('Open Application')").click()
                page.wait_for_timeout(1000)

                # Verify Application Details drawer opened and contains GitHub repository section
                drawer = page.locator(f"h2:has-text('{app_name}')")
                assert drawer.is_visible(), f"Application drawer for {app_name} did not open"

                github_section = page.locator("text=Repository").first
                assert github_section.is_visible(), "Application details drawer missing Repository section"
                print("  ✓ Application Details drawer displays GitHub repository metadata")

                # Phase 4 CI Automation verification in Details Drawer
                ci_section = page.locator("text=CI Automation").first
                assert ci_section.is_visible(), "Application details drawer missing CI Automation section"

                # Check CI Refresh button
                ci_refresh_btn = page.locator("#refresh-ci-btn").first
                if ci_refresh_btn.is_visible():
                    ci_refresh_btn.click()
                    page.wait_for_timeout(500)
                    print("  ✓ CI status refreshed via drawer button")

                print("  ✓ Application Details drawer displays CI Automation card and controls")

                # Phase 5 Container Image verification in Details Drawer
                img_section = page.locator("#app-detail-container-image-section").first
                assert img_section.is_visible(), "Application details drawer missing Container Image section"
                assert img_section.locator("text=GHCR").first.is_visible(), "GHCR registry badge missing in Container Image section"

                repo_elem = page.locator("#container-image-repo").first
                assert repo_elem.is_visible(), "Container image repository element missing"
                print(f"  ✓ Container Image repository rendered: {repo_elem.inner_text()}")

                copy_btn = page.locator("#copy-image-ref-btn").first
                assert copy_btn.is_visible(), "Copy Image button missing"
                copy_btn.click()
                page.wait_for_timeout(300)
                assert page.locator("text=Copied!").is_visible(), "Copy button did not transition to Copied! state"
                print("  ✓ Copy container image reference verified in UI")

                sync_btn = page.locator("#refresh-image-btn").first
                if sync_btn.is_visible():
                    sync_btn.click()
                    page.wait_for_timeout(500)
                    print("  ✓ Container image sync triggered via UI button")

                self.test_results[f"Provisioning {tpl_display}"] = "PASS"
            except Exception as e:
                self.test_results[f"Provisioning {tpl_display}"] = f"FAIL: {e}"
                print(f"  ❌ Provisioning {tpl_display} failed: {e}")
            finally:
                page.close()

    # =========================================================================
    # 3. RESPONSIVE TESTING
    # =========================================================================
    def test_responsive_layouts(self):
        print("\n--- [PLAYWRIGHT] Testing Responsive Viewports ---")
        viewports = [
            ("Desktop 1920x1080", {"width": 1920, "height": 1080}),
            ("Desktop 1366x768", {"width": 1366, "height": 768}),
            ("Tablet 768x1024", {"width": 768, "height": 1024}),
            ("Mobile 390x844", {"width": 390, "height": 844}),
            ("Mobile 375x667", {"width": 375, "height": 667})
        ]

        for vp_name, vp_dim in viewports:
            page = self.create_monitored_page(viewport=vp_dim)
            try:
                page.goto(f"{BASE_URL}/", wait_until="networkidle")
                # Ensure no horizontal scrollbar overflow
                scroll_width = page.evaluate("document.documentElement.scrollWidth")
                client_width = page.evaluate("document.documentElement.clientWidth")
                assert scroll_width <= client_width + 5, f"Horizontal overflow detected in {vp_name}: {scroll_width} > {client_width}"

                # Test Create Application page on this viewport
                page.goto(f"{BASE_URL}/create-application", wait_until="networkidle")
                assert page.locator("text=Create Application").is_visible(), f"Create app header missing on {vp_name}"
                print(f"  ✓ {vp_name} renders cleanly without overflow")
                self.test_results[f"Responsive: {vp_name}"] = "PASS"
            except Exception as e:
                self.test_results[f"Responsive: {vp_name}"] = f"FAIL: {e}"
                print(f"  ❌ {vp_name} failed: {e}")
            finally:
                page.close()

    # =========================================================================
    # 4. RUN ALL PLAYWRIGHT TESTS
    # =========================================================================
    def run_all(self):
        self.setup()
        try:
            self.test_navigation_and_views()
            self.test_create_application_templates()
            self.test_responsive_layouts()
        finally:
            self.teardown()

        print("\n==================================================")
        print("PLAYWRIGHT TEST SUMMARY")
        print("==================================================")
        all_passed = True
        for name, status in self.test_results.items():
            print(f"[{status}] {name}")
            if not status.startswith("PASS"):
                all_passed = False

        print(f"\nTotal Console Errors logged: {len(self.console_errors)}")
        for err in self.console_errors[:5]:
            print(f"  {err}")
        print(f"Total Page Errors: {len(self.page_errors)}")
        print(f"Total Failed Network Requests: {len(self.failed_requests)}")

        return all_passed, self.test_results


if __name__ == "__main__":
    suite = PlaywrightQASuite()
    success, results = suite.run_all()
    sys.exit(0 if success else 1)
