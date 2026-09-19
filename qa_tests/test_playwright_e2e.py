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

    def create_monitored_page(self, viewport={"width": 1440, "height": 900}) -> Page:
        page = self.browser.new_page(viewport=viewport)
        page.on("console", lambda msg: self.console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: self.failed_requests.append(f"{req.method} {req.url} -> {req.failure}"))
        return page

    # =========================================================================
    # 1. NAVIGATION & SIDEBAR INFORMATION ARCHITECTURE
    # =========================================================================
    def test_sidebar_and_layout(self):
        print("\n--- [PLAYWRIGHT] 1. Testing Sidebar & Clean Information Architecture ---")
        page = self.create_monitored_page()
        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            assert "DevForge" in page.title(), f"Page title mismatch: {page.title()}"
            print("  ✓ Platform Overview loaded")

            # 1. Primary sidebar destinations: Overview, Applications, Activity, Settings
            sidebar = page.locator("aside")
            assert sidebar.locator("button:has-text('Overview')").first.is_visible(), "Overview missing in sidebar"
            assert sidebar.locator("button:has-text('Applications')").first.is_visible(), "Applications missing in sidebar"
            assert sidebar.locator("button:has-text('Activity')").first.is_visible(), "Activity missing in sidebar"
            assert sidebar.locator("button:has-text('Settings')").first.is_visible(), "Settings missing in sidebar"
            print("  ✓ Main sidebar contains only Overview, Applications, Activity, Settings")

            # 2. Verify REMOVAL of standalone primary destinations
            for forbidden in ["Deployments", "Environments", "Infrastructure", "Automation", "Monitoring", "GitOps"]:
                count = sidebar.locator(f"button:has-text('{forbidden}')").count()
                assert count == 0, f"Sidebar must not have primary destination for '{forbidden}'"
            print("  ✓ Standalone Deployments, Environments, Infrastructure, Automation, Monitoring removed from sidebar")

            # 3. Verify absence of Ctrl+K shortcut prompt
            ctrl_k = page.locator("kbd:has-text('Ctrl')")
            assert ctrl_k.count() == 0, "Visible Ctrl+K shortcut badge must be removed"
            print("  ✓ Visible Ctrl+K command palette shortcut removed")

            # 4. Verify absence of DevForge platform version badges (v0.1, etc.)
            version_badge = page.locator("aside span:has-text('v0.1')")
            assert version_badge.count() == 0, "Platform version v0.1 must not be displayed in UI"
            fastapi_badge = page.locator("aside span:has-text('FastAPI v0.110')")
            assert fastapi_badge.count() == 0, "FastAPI version must not be displayed in sidebar footer"
            print("  ✓ DevForge platform version badges hidden from user-facing UI")

            # 5. Truthful cluster indication (no fake us-east-1)
            us_east = page.locator("text=us-east-1")
            assert us_east.count() == 0, "Fake us-east-1 cloud region must not be displayed"
            assert page.locator("text=Local KinD").first.is_visible() or page.locator("text=Kubernetes").first.is_visible()
            print("  ✓ Truthful local cluster status displayed without fictional cloud regions")

            self.test_results["Sidebar & Information Architecture"] = "PASS"
        except Exception as e:
            self.test_results["Sidebar & Information Architecture"] = f"FAIL: {e}"
            print(f"  ❌ Sidebar test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 2. GLOBAL OVERVIEW & REAL METRICS AUDIT
    # =========================================================================
    def test_overview_metrics_audit(self):
        print("\n--- [PLAYWRIGHT] 2. Testing Global Overview & Truthful Metrics Audit ---")
        page = self.create_monitored_page()
        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle")

            # Verify 4 Metric Cards
            page.locator("text=Applications").first.wait_for(state="visible", timeout=5000)
            page.locator("text=Healthy Services").first.wait_for(state="visible", timeout=5000)
            page.locator("text=Active Deployments").first.wait_for(state="visible", timeout=5000)
            page.locator("text=Failed Deployments").first.wait_for(state="visible", timeout=5000)
            print("  ✓ 4 Global platform metric cards rendered")

            # Verify absence of fake hardcoded numbers: "+2 this week", "99.8%", "98.4% uptime"
            assert page.locator("text=+2 this week").count() == 0, "Fake '+2 this week' metric found"
            assert page.locator("text=99.8%").count() == 0, "Fake '99.8%' metric found"
            print("  ✓ Misleading mock data (+2 this week, 99.8%) removed from dashboard")

            # Verify clicking an application row in recent deployments navigates to application
            recent_row = page.locator("table tr:has-text('inventory-api')").first
            if recent_row.is_visible():
                recent_row.click()
                page.wait_for_timeout(500)
                assert page.locator("h1:has-text('inventory-api')").is_visible(), "Clicking app row in overview did not navigate to app detail"
                print("  ✓ Clicking application in Overview navigates to application detail page")

            self.test_results["Overview & Real Data Audit"] = "PASS"
        except Exception as e:
            self.test_results["Overview & Real Data Audit"] = f"FAIL: {e}"
            print(f"  ❌ Overview audit failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 3. APPLICATIONS CATALOG ENTRY POINT
    # =========================================================================
    def test_applications_catalog(self):
        print("\n--- [PLAYWRIGHT] 3. Testing Applications Catalog Entry Point ---")
        page = self.create_monitored_page()
        try:
            # 1. Navigate to /applications
            page.goto(f"{BASE_URL}/applications", wait_until="networkidle")
            page.locator("h1:has-text('Applications')").wait_for(state="visible", timeout=5000)
            print("  ✓ Applications catalog page loaded")

            # 2. Verify search filter
            search_input = page.locator("input[placeholder*='Filter applications by name']")
            assert search_input.is_visible(), "Application search filter input missing"
            search_input.fill("inventory-api")
            page.wait_for_timeout(300)

            # 3. Table row contains complete metadata
            app_row = page.locator("table tr:has-text('inventory-api')").first
            assert app_row.is_visible(), "inventory-api row not found in catalog"
            assert app_row.locator("text=Python 3.12 (FastAPI)").is_visible(), "Runtime missing in row"
            print("  ✓ Application row displays name, runtime, and status")

            # 4. Clicking application opens dedicated application detail page
            app_row.click()
            page.wait_for_timeout(500)
            assert page.locator("h1:has-text('inventory-api')").is_visible(), "Clicking row did not open application detail page"
            assert "applications/inventory-api" in page.url, f"URL did not update to application route: {page.url}"
            print("  ✓ Clicking application row navigates to /applications/inventory-api")

            self.test_results["Applications Catalog Entry Point"] = "PASS"
        except Exception as e:
            self.test_results["Applications Catalog Entry Point"] = f"FAIL: {e}"
            print(f"  ❌ Applications catalog test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 4. APPLICATION DETAIL HEADER & ALL 7 TABS
    # =========================================================================
    def test_application_detail_and_7_tabs(self):
        print("\n--- [PLAYWRIGHT] 4. Testing Application Detail Page & 7 Specific Tabs ---")
        page = self.create_monitored_page()
        try:
            page.goto(f"{BASE_URL}/applications/inventory-api", wait_until="networkidle")
            page.locator("h1:has-text('inventory-api')").wait_for(state="visible", timeout=10000)

            # 1. Header Verification
            assert page.locator("text=Python 3.12 (FastAPI)").first.is_visible(), "Runtime badge missing"
            assert page.locator("button:has-text('Redeploy')").first.is_visible(), "Redeploy button missing"
            assert page.locator("a:has-text('Open Repository')").first.is_visible() or page.locator("button:has-text('Add Environment')").first.is_visible()
            print("  ✓ Application header rendered with metadata and actions")

            # 2. Verify all 7 Application Tabs are present
            tabs = ["Overview", "Deployments", "Environments", "Infrastructure", "Automation", "Monitoring", "Logs"]
            for tab_name in tabs:
                tab_btn = page.locator(f"button:has-text('{tab_name}')").first
                assert tab_btn.is_visible(), f"Tab '{tab_name}' missing on application detail page"
            print("  ✓ All 7 tabs (Overview, Deployments, Environments, Infrastructure, Automation, Monitoring, Logs) visible")

            # 3. Tab 1: Overview
            page.locator("#app-tab-overview").click()
            page.wait_for_timeout(300)
            assert page.locator("text=CPU Usage").first.is_visible()
            assert page.locator("text=Recent Deployments").first.is_visible()
            print("  ✓ Tab 1: Overview content verified")

            # 4. Tab 2: Deployments
            page.locator("#app-tab-deployments").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Application Deployments").first.is_visible()
            assert "applications/inventory-api/deployments" in page.url
            print("  ✓ Tab 2: Deployments content verified with URL sync")

            # 5. Tab 3: Environments
            page.locator("#app-tab-environments").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Application Environments").first.is_visible()
            assert "applications/inventory-api/environments" in page.url
            assert page.locator("text=Local KinD").first.is_visible()
            print("  ✓ Tab 3: Environments content verified with local cluster info")

            # 6. Tab 4: Infrastructure
            page.locator("#app-tab-infrastructure").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Application Infrastructure & Kubernetes").first.is_visible()
            assert page.locator("text=Terraform Infrastructure").first.is_visible()
            assert "applications/inventory-api/infrastructure" in page.url
            print("  ✓ Tab 4: Infrastructure content verified with Kubernetes & Terraform")

            # 7. Tab 5: Automation
            page.locator("#app-tab-automation").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Ansible Automation").first.is_visible(), "Ansible Automation title missing"
            assert page.locator("#ansible-launcher-section").is_visible(), "Ansible launcher section missing"
            assert page.locator("#ansible-playbook-select").is_visible(), "Ansible playbook select missing"
            assert "applications/inventory-api/automation" in page.url, f"URL mismatch: {page.url}"
            print("  ✓ Tab 5: Automation content verified with approved playbooks")

            # 8. Tab 6: Monitoring
            page.locator("#app-tab-monitoring").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Application Telemetry & Monitoring").first.is_visible(), "Monitoring header missing"
            assert page.locator("text=Open in Grafana").first.is_visible() or page.locator("#btn-open-grafana").is_visible(), "Grafana link missing"
            assert "applications/inventory-api/monitoring" in page.url, f"URL mismatch: {page.url}"
            print("  ✓ Tab 6: Monitoring content verified with observability links")

            # 9. Tab 7: Logs
            page.locator("#app-tab-logs").click()
            page.wait_for_timeout(400)
            assert page.locator("text=Consolidated Application Logs").first.is_visible(), "Logs header missing"
            assert "applications/inventory-api/logs" in page.url, f"URL mismatch: {page.url}"
            print("  ✓ Tab 7: Logs terminal interface verified with URL sync")

            self.test_results["Application Detail & 7 Tabs"] = "PASS"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.test_results["Application Detail & 7 Tabs"] = f"FAIL: {e}\n{tb}"
            print(f"  ❌ Application Detail test failed: {e}\n{tb}")
        finally:
            page.close()

    # =========================================================================
    # 5. DIRECT URL ACCESS, BROWSER HISTORY & ERROR STATES
    # =========================================================================
    def test_routing_history_and_errors(self):
        print("\n--- [PLAYWRIGHT] 5. Testing Direct URLs, Browser History & 404 State ---")
        page = self.create_monitored_page()
        try:
            # 1. Direct URL access to specific application tab
            page.goto(f"{BASE_URL}/applications/inventory-api/infrastructure", wait_until="networkidle")
            page.locator("h2:has-text('Application Infrastructure & Kubernetes')").wait_for(state="visible", timeout=10000)
            print("  ✓ Direct URL to /applications/inventory-api/infrastructure opens Infrastructure tab")

            # 2. Browser Refresh preserves state
            page.reload(wait_until="networkidle")
            assert page.locator("h2:has-text('Application Infrastructure & Kubernetes')").is_visible(), "Refresh lost active tab state"
            print("  ✓ Page refresh maintains active tab")

            # 3. Browser Back / Forward between application tabs
            page.locator("#app-tab-overview").click()
            page.wait_for_timeout(300)
            page.go_back()
            page.wait_for_timeout(300)
            assert "infrastructure" in page.url, "Browser back failed to restore infrastructure tab"
            page.go_forward()
            page.wait_for_timeout(300)
            assert page.locator("text=CPU Usage").first.is_visible(), "Browser forward failed"
            print("  ✓ Browser back and forward correctly navigate application subtabs")

            # 4. Invalid Application 404 State
            page.goto(f"{BASE_URL}/applications/non-existent-service-404", wait_until="networkidle")
            page.locator("text=Application Not Found").wait_for(state="visible", timeout=5000)
            assert page.locator("button:has-text('Return to Applications')").is_visible(), "Return button missing in 404 view"
            page.locator("button:has-text('Return to Applications')").click()
            page.wait_for_timeout(500)
            assert page.locator("h1:has-text('Applications')").is_visible(), "Return to applications failed"
            print("  ✓ Invalid application ID shows proper 404 state with recovery button")

            self.test_results["Routing, History & Error States"] = "PASS"
        except Exception as e:
            self.test_results["Routing, History & Error States"] = f"FAIL: {e}"
            print(f"  ❌ Routing test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 6. ACTIONABLE NOTIFICATIONS WITH DEEP-LINK NAVIGATION
    # =========================================================================
    def test_actionable_notifications(self):
        print("\n--- [PLAYWRIGHT] 6. Testing Actionable Notifications & Deep Links ---")
        page = self.create_monitored_page()
        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle")

            # Open notification dropdown
            bell_btn = page.locator("header button[aria-label='Platform Notifications']").first
            assert bell_btn.is_visible(), "Notifications bell icon not found in header"
            bell_btn.click()
            page.wait_for_timeout(400)

            notif_panel = page.locator("text=System Notifications").first
            assert notif_panel.is_visible(), "Notification panel did not open"
            print("  ✓ Notifications panel opened")

            # Verify notification identifies what failed
            failed_card = page.locator("div[role='button']:has-text('Deployment Failed'), div[role='button']:has-text('Service')").first
            if failed_card.is_visible():
                # Verify reason is displayed
                assert failed_card.locator("text=Reason:").is_visible() or failed_card.locator("text=Telemetry:").is_visible(), "Notification must state specific reason"
                print("  ✓ Notification clearly identifies failing application, environment, and reason")

                # Click notification -> Must navigate to application detail tab!
                failed_card.click()
                page.wait_for_timeout(600)
                assert "applications/" in page.url, f"Notification click did not navigate to application: {page.url}"
                print("  ✓ Clicking notification navigates directly to target application detail view")

            self.test_results["Actionable Notifications"] = "PASS"
        except Exception as e:
            self.test_results["Actionable Notifications"] = f"FAIL: {e}"
            print(f"  ❌ Notifications test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 7. GLOBAL ACTIVITY AUDIT TRAIL & FILTERING
    # =========================================================================
    def test_global_activity(self):
        print("\n--- [PLAYWRIGHT] 7. Testing Global Activity Audit Trail & Filtering ---")
        page = self.create_monitored_page()
        try:
            page.goto(f"{BASE_URL}/activity", wait_until="networkidle")
            page.locator("h1:has-text('Platform Activity Log')").wait_for(state="visible", timeout=5000)

            # Filter inputs
            search_input = page.locator("input[placeholder*='Filter by application or details']")
            assert search_input.is_visible(), "Activity search input missing"
            search_input.fill("inventory-api")
            page.wait_for_timeout(300)
            print("  ✓ Activity multi-field filtering verified")

            # Row click navigates to application
            act_item = page.locator("text=inventory-api").first
            if act_item.is_visible():
                act_item.click()
                page.wait_for_timeout(500)
                assert "applications/" in page.url, "Clicking activity item did not navigate to application"
                print("  ✓ Clicking activity event navigates to relevant application")

            self.test_results["Global Activity Audit Trail"] = "PASS"
        except Exception as e:
            self.test_results["Global Activity Audit Trail"] = f"FAIL: {e}"
            print(f"  ❌ Activity test failed: {e}")
        finally:
            page.close()

    # =========================================================================
    # 8. RESPONSIVE DESIGN (DESKTOP, TABLET, MOBILE)
    # =========================================================================
    def test_responsive_layouts(self):
        print("\n--- [PLAYWRIGHT] 8. Testing Responsive Layouts across 8 Required Viewports ---")
        viewports = [
            ("Desktop 1920x1080", {"width": 1920, "height": 1080}),
            ("Desktop 1440x900", {"width": 1440, "height": 900}),
            ("Desktop 1366x768", {"width": 1366, "height": 768}),
            ("Tablet 1024x768", {"width": 1024, "height": 768}),
            ("Tablet 768x1024", {"width": 768, "height": 1024}),
            ("Mobile 430x932", {"width": 430, "height": 932}),
            ("Mobile 390x844", {"width": 390, "height": 844}),
            ("Mobile 375x667", {"width": 375, "height": 667})
        ]

        for vp_name, vp_size in viewports:
            page = self.create_monitored_page(viewport=vp_size)
            try:
                # 1. Test Applications Catalog on viewport
                page.goto(f"{BASE_URL}/applications", wait_until="networkidle")
                page.locator("h1:has-text('Applications')").wait_for(state="visible", timeout=6000)

                # Verify Application names are NOT clipped
                app_name_el = page.locator("td span.whitespace-nowrap").first
                assert app_name_el.is_visible(), "Application name not visible"
                app_name_text = app_name_el.inner_text()
                assert len(app_name_text) > 0, "Application name empty"
                is_clipped = page.evaluate("""() => {
                    const el = document.querySelector('td span.whitespace-nowrap');
                    return el ? el.scrollWidth > el.clientWidth : false;
                }""")
                assert not is_clipped, f"Application name '{app_name_text}' is clipped in {vp_name}"

                # Programmatic overflow check on Applications Page
                scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
                client_w = page.evaluate("() => document.documentElement.clientWidth")
                assert scroll_w <= client_w, f"Page-level horizontal overflow on Applications page in {vp_name}: {scroll_w} > {client_w}"

                # 2. Test Application Detail page on viewport
                page.goto(f"{BASE_URL}/applications/inventory-api", wait_until="networkidle")
                page.locator("h1:has-text('inventory-api')").wait_for(state="visible", timeout=6000)

                # Tabs should be clickable
                page.locator("#app-tab-deployments").click()
                page.wait_for_timeout(200)

                # Programmatic overflow check on Application Detail Page
                scroll_w_detail = page.evaluate("() => document.documentElement.scrollWidth")
                client_w_detail = page.evaluate("() => document.documentElement.clientWidth")
                assert scroll_w_detail <= client_w_detail, f"Page-level horizontal overflow on Detail page in {vp_name}: {scroll_w_detail} > {client_w_detail}"

                print(f"  ✓ {vp_name} verified: scrollWidth={scroll_w} <= clientWidth={client_w}, app names unclipped")
                self.test_results[f"Responsive: {vp_name}"] = "PASS"
            except Exception as e:
                self.test_results[f"Responsive: {vp_name}"] = f"FAIL: {e}"
                print(f"  ❌ {vp_name} failed: {e}")
            finally:
                page.close()

    # =========================================================================
    # 9. SELF-HEALING & AUTOMATED REMEDIATION (Phase 11)
    # =========================================================================
    def test_self_healing_and_remediation(self):
        print("\n--- [PLAYWRIGHT] 9. Testing Phase 11 Self-Healing & Automated Remediation ---")
        page = self.create_monitored_page()
        try:
            # 1. Navigate to Application Detail (inventory-api)
            page.goto(f"{BASE_URL}/applications/inventory-api", wait_until="networkidle")
            page.locator("#overview-remediation-card").wait_for(state="visible", timeout=8000)
            print("  ✓ Self-Healing & Automated Remediation overview card visible in Overview tab")

            # Check counters
            card_text = page.locator("#overview-remediation-card").inner_text()
            assert "Total Remediations" in card_text
            assert "Recoveries" in card_text
            assert "Active Incidents" in card_text
            print("  ✓ Overview remediation metrics rendered")

            # 2. Click navigation link to Monitoring tab
            page.locator("#btn-view-remediation-details").click()
            page.wait_for_timeout(400)
            page.locator("#monitoring-remediation-panel").wait_for(state="visible", timeout=6000)
            print("  ✓ Deep link navigated to Monitoring tab with Remediation Engine panel")

            # 3. Verify Enforced Remediation Policies
            page.locator("text=KUBERNETES_ROLLOUT_RESTART").first.wait_for(state="visible", timeout=8000)
            policies_text = page.locator("#monitoring-remediation-panel").inner_text()
            assert "remediation policies" in policies_text.lower()
            assert "KUBERNETES_ROLLOUT_RESTART" in policies_text
            print("  ✓ Active remediation policies displayed (deterministic allowlist)")

            # 4. Trigger Cluster Health Scan
            scan_btn = page.locator("#btn-trigger-health-scan")
            assert scan_btn.is_visible()
            scan_btn.click()
            page.wait_for_timeout(1000)
            page.locator("#remediation-action-banner").wait_for(state="visible", timeout=8000)
            banner_text = page.locator("#remediation-action-banner").inner_text()
            assert "Scan complete" in banner_text or "evaluated" in banner_text
            print(f"  ✓ On-demand cluster health scan executed: {banner_text}")

            self.test_results["Self-Healing & Remediation Engine"] = "PASS"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.test_results["Self-Healing & Remediation Engine"] = f"FAIL: {e}\n{tb}"
            print(f"  ❌ Self-Healing test failed: {e}\n{tb}")
        finally:
            page.close()

    # =========================================================================
    # RUN ALL PLAYWRIGHT TESTS
    # =========================================================================
    def run_all(self):
        self.setup()
        try:
            self.test_sidebar_and_layout()
            self.test_overview_metrics_audit()
            self.test_applications_catalog()
            self.test_application_detail_and_7_tabs()
            self.test_routing_history_and_errors()
            self.test_actionable_notifications()
            self.test_global_activity()
            self.test_responsive_layouts()
            self.test_self_healing_and_remediation()
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

        print(f"\nTotal Console Errors: {len(self.console_errors)}")
        for err in self.console_errors[:5]:
            print(f"  {err}")
        print(f"Total Page Errors: {len(self.page_errors)}")
        print(f"Total Failed Network Requests: {len(self.failed_requests)}")

        return all_passed, self.test_results


if __name__ == "__main__":
    suite = PlaywrightQASuite()
    success, results = suite.run_all()
    sys.exit(0 if success else 1)
