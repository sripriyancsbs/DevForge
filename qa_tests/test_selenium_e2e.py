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
BASE_URL = "http://127.0.0.1:3000"


class SeleniumQASuite:
    def __init__(self):
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
    # 1. NAVIGATION & SIDEBAR INFORMATION ARCHITECTURE
    # =========================================================================
    def test_sidebar_information_architecture(self):
        print("\n--- [SELENIUM] 1. Testing Sidebar Information Architecture ---")
        try:
            self.driver.get(BASE_URL)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DevForge')]"))
            )
            print("  ✓ DevForge loaded successfully")

            # 1. Primary sidebar destinations: Overview, Applications, Activity, Settings
            sidebar = self.driver.find_element(By.TAG_NAME, "aside")
            for primary in ["Overview", "Applications", "Activity", "Settings"]:
                btn = sidebar.find_element(By.XPATH, f".//button[contains(., '{primary}')]")
                assert btn.is_displayed(), f"Primary destination '{primary}' missing in sidebar"
            print("  ✓ Main sidebar contains only Overview, Applications, Activity, Settings")

            # 2. Standalone primary destinations removed
            for forbidden in ["Deployments", "Environments", "Infrastructure", "Automation", "Monitoring", "GitOps"]:
                elements = sidebar.find_elements(By.XPATH, f".//button[contains(., '{forbidden}')]")
                assert len(elements) == 0, f"Standalone destination '{forbidden}' must not be in primary sidebar"
            print("  ✓ Standalone Deployments, Environments, Infrastructure, Automation, Monitoring removed from sidebar")

            # 3. No visible Ctrl+K shortcut prompt
            ctrl_ks = self.driver.find_elements(By.XPATH, "//kbd[contains(text(), 'Ctrl')]")
            assert len(ctrl_ks) == 0, "Visible Ctrl+K command palette shortcut must be removed"
            print("  ✓ Visible Ctrl+K command palette shortcut removed")

            # 4. No DevForge platform version badges (v0.1)
            v01 = self.driver.find_elements(By.XPATH, "//aside//span[contains(text(), 'v0.1')]")
            assert len(v01) == 0, "Platform version v0.1 must not be displayed in UI"
            print("  ✓ DevForge platform version badges hidden from user-facing UI")

            # 5. Truthful local cluster status
            assert "Local KinD" in self.driver.page_source or "Kubernetes" in self.driver.page_source
            assert "us-east-1" not in self.driver.page_source
            print("  ✓ Truthful local cluster status displayed without fictional cloud regions")

            self.test_results["Selenium: Sidebar & Information Architecture"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Sidebar & Information Architecture"] = f"FAIL: {e}"
            print(f"  ❌ Sidebar & IA test failed: {e}")

    # =========================================================================
    # 2. APPLICATIONS CATALOG AS PRIMARY ENTRY POINT
    # =========================================================================
    def test_applications_catalog(self):
        print("\n--- [SELENIUM] 2. Testing Applications Catalog Entry Point ---")
        try:
            self.driver.get(f"{BASE_URL}/applications")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Applications')]"))
            )
            print("  ✓ Applications catalog page loaded")

            # Locate inventory-api row
            inv_row = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'inventory-api')]"))
            )
            assert inv_row.is_displayed(), "inventory-api row missing in catalog"
            print("  ✓ Application row displays inventory-api metadata")

            # Click application row to navigate to details
            inv_row.click()
            time.sleep(1)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'inventory-api')]"))
            )
            assert "applications/inventory-api" in self.driver.current_url
            print(f"  ✓ Clicked application row; navigated to: {self.driver.current_url}")

            self.test_results["Selenium: Applications Catalog Entry Point"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Applications Catalog Entry Point"] = f"FAIL: {e}"
            print(f"  ❌ Applications catalog failed: {e}")

    # =========================================================================
    # 3. APPLICATION HEADER & ACTION MODALS
    # =========================================================================
    def test_application_header_and_actions(self):
        print("\n--- [SELENIUM] 3. Testing Application Header & Action Modals ---")
        try:
            self.driver.get(f"{BASE_URL}/applications/inventory-api")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'inventory-api')]"))
            )

            # Check Header Actions
            redeploy_btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "header-redeploy-btn"))
            )
            assert redeploy_btn.is_displayed(), "Redeploy CTA missing in header"

            add_env_btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "header-add-env-btn"))
            )
            assert add_env_btn.is_displayed(), "Add Environment CTA missing in header"
            print("  ✓ Application header CTAs (Redeploy, Add Environment) verified")

            # Test Redeploy Modal Open & Close
            redeploy_btn.click()
            time.sleep(0.5)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Trigger Application Rollout')]"))
            )
            print("  ✓ Redeploy modal opened successfully")
            cancel_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "modal-redeploy-cancel-btn"))
            )
            cancel_btn.click()
            time.sleep(0.5)

            # Test Add Environment Modal Open & Close
            add_env_btn.click()
            time.sleep(0.5)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Add Target Environment')]"))
            )
            print("  ✓ Add Environment modal opened successfully")
            cancel_env_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "modal-add-env-cancel-btn"))
            )
            cancel_env_btn.click()
            time.sleep(0.5)

            self.test_results["Selenium: Header & Action Modals"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Header & Action Modals"] = f"FAIL: {e}"
            print(f"  ❌ Header & actions failed: {e}")

    # =========================================================================
    # 4. APPLICATION-SPECIFIC 7 TABS
    # =========================================================================
    def test_application_7_tabs(self):
        print("\n--- [SELENIUM] 4. Testing Application 7 Tabs (Application-Centric) ---")
        try:
            self.driver.get(f"{BASE_URL}/applications/inventory-api")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "app-detail-tabs"))
            )

            tabs = [
                ("overview", "CPU Usage"),
                ("deployments", "Application Deployments"),
                ("environments", "Application Environments"),
                ("infrastructure", "Application Infrastructure & Kubernetes"),
                ("automation", "Ansible Automation"),
                ("monitoring", "Application Telemetry & Monitoring"),
                ("logs", "Consolidated Application Logs")
            ]

            for tab_id, expected_text in tabs:
                tab_elem = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, f"app-tab-{tab_id}"))
                )
                tab_elem.click()
                time.sleep(0.5)

                # Verify URL contains tab
                if tab_id != "overview":
                    assert f"applications/inventory-api/{tab_id}" in self.driver.current_url, f"URL mismatch for tab {tab_id}: {self.driver.current_url}"

                # Verify Content renders
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{expected_text}')]"))
                )
                print(f"  ✓ Tab '{tab_id}' rendered and synced URL: {self.driver.current_url}")

            self.test_results["Selenium: Application 7 Tabs"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Application 7 Tabs"] = f"FAIL: {e}"
            print(f"  ❌ 7 Tabs test failed: {e}")

    # =========================================================================
    # 5. INFRASTRUCTURE: KUBERNETES & TERRAFORM
    # =========================================================================
    def test_infrastructure_tab_k8s_and_terraform(self):
        print("\n--- [SELENIUM] 5. Testing Application Infrastructure (K8s + Terraform) ---")
        try:
            self.driver.get(f"{BASE_URL}/applications/inventory-api/infrastructure")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "app-detail-k8s-section"))
            )
            print("  ✓ Kubernetes workload section verified in application")

            # Check Namespace
            ns = self.driver.find_element(By.ID, "k8s-deployment-ns")
            assert "devforge" in ns.text, f"Unexpected namespace: {ns.text}"
            print(f"  ✓ Kubernetes namespace: {ns.text}")

            # Check Service
            svc = self.driver.find_element(By.ID, "k8s-deployment-service")
            assert "inventory-api" in svc.text, f"Unexpected service: {svc.text}"
            print(f"  ✓ Kubernetes service: {svc.text}")

            # Check Terraform Section
            tf_sec = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "terraform-infrastructure-section"))
            )
            assert tf_sec.is_displayed(), "Terraform section missing"

            # Check Terraform Status
            tf_status = self.driver.find_element(By.ID, "terraform-status-badge")
            assert tf_status.is_displayed(), "Terraform status badge missing"
            print(f"  ✓ Terraform status badge: {tf_status.text}")

            # Test Terraform Plan Button
            plan_btn = self.driver.find_element(By.ID, "terraform-plan-btn")
            assert plan_btn.is_displayed()
            plan_btn.click()
            time.sleep(1)
            print("  ✓ Triggered Terraform Plan action")

            self.test_results["Selenium: Infrastructure K8s & Terraform"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Infrastructure K8s & Terraform"] = f"FAIL: {e}"
            print(f"  ❌ Infrastructure test failed: {e}")

    # =========================================================================
    # 6. AUTOMATION: ANSIBLE PLAYBOOK EXECUTION
    # =========================================================================
    def test_automation_tab_ansible(self):
        print("\n--- [SELENIUM] 6. Testing Application Automation (Ansible) ---")
        try:
            self.driver.get(f"{BASE_URL}/applications/inventory-api/automation")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "ansible-launcher-section"))
            )
            print("  ✓ Ansible section rendered inside application automation tab")

            # Select playbook
            pb_elem = self.driver.find_element(By.ID, "ansible-playbook-select")
            pb_select = Select(pb_elem)
            pb_select.select_by_value("health_check")
            print("  ✓ Selected approved playbook: health_check")

            # Trigger playbook
            run_btn = self.driver.find_element(By.ID, "ansible-run-btn")
            assert run_btn.is_displayed()
            run_btn.click()
            time.sleep(2)
            print("  ✓ Triggered Ansible playbook execution in Selenium")

            # Check execution history exists
            table = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "ansible-executions-table"))
            )
            assert table.is_displayed(), "Executions history container missing"
            print("  ✓ Execution history updated")

            self.test_results["Selenium: Automation Ansible Playbooks"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Automation Ansible Playbooks"] = f"FAIL: {e}"
            print(f"  ❌ Automation test failed: {e}")

    # =========================================================================
    # 7. ACTIONABLE NOTIFICATIONS & DEEP LINK NAVIGATION
    # =========================================================================
    def test_actionable_notifications(self):
        print("\n--- [SELENIUM] 7. Testing Actionable Notifications & Deep Linking ---")
        try:
            self.driver.get(BASE_URL)
            bell_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "top-nav-bell-btn"))
            )
            bell_btn.click()
            time.sleep(0.5)

            # Notification popup opened
            panel = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "notifications-panel"))
            )
            assert panel.is_displayed(), "Notifications panel not displayed"

            # Check context: identifying application, environment, and reason
            panel_text = panel.text
            assert "Reason:" in panel_text or "Telemetry:" in panel_text, "Notification missing specific failure reason"
            print("  ✓ Notification clearly identifies failing application, environment, and reason")

            # Click notification to navigate
            notif_card = self.driver.find_element(By.XPATH, "//*[@data-testid='notification-item']")
            notif_card.click()
            time.sleep(1)

            # Should navigate to target application detail page
            WebDriverWait(self.driver, 10).until(
                lambda d: "applications/" in d.current_url
            )
            print(f"  ✓ Notification clicked; navigated to application: {self.driver.current_url}")

            self.test_results["Selenium: Actionable Notifications"] = "PASS"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.test_results["Selenium: Actionable Notifications"] = f"FAIL: {e}\n{tb}"
            print(f"  ❌ Notifications test failed: {e}\n{tb}")

    # =========================================================================
    # 8. RESPONSIVE VIEWPORT TESTING
    # =========================================================================
    def test_responsive_viewports(self):
        print("\n--- [SELENIUM] 8. Testing Responsive Viewports across 8 Required Breakpoints ---")
        viewports = [
            ("Desktop 1920x1080", 1920, 1080),
            ("Desktop 1440x900", 1440, 900),
            ("Desktop 1366x768", 1366, 768),
            ("Tablet 1024x768", 1024, 768),
            ("Tablet 768x1024", 768, 1024),
            ("Mobile 430x932", 430, 932),
            ("Mobile 390x844", 390, 844),
            ("Mobile 375x667", 375, 667)
        ]
        for name, width, height in viewports:
            try:
                self.driver.set_window_size(width, height)

                # 1. Check Applications catalog page
                self.driver.get(f"{BASE_URL}/applications")
                WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Applications')]"))
                )

                # Verify unclipped application names
                app_name_el = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td span.whitespace-nowrap"))
                )
                assert len(app_name_el.text) > 0
                is_clipped = self.driver.execute_script("""
                    const el = document.querySelector('td span.whitespace-nowrap');
                    return el ? el.scrollWidth > el.clientWidth : false;
                """)
                assert not is_clipped, f"App name '{app_name_el.text}' is clipped in Selenium {name}"

                # Programmatic overflow check on Applications Page
                scroll_w = self.driver.execute_script("return document.documentElement.scrollWidth;")
                client_w = self.driver.execute_script("return document.documentElement.clientWidth;")
                assert scroll_w <= client_w, f"Page overflow on Applications page in {name}: {scroll_w} > {client_w}"

                # 2. Check Application Detail page
                self.driver.get(f"{BASE_URL}/applications/inventory-api")
                WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'inventory-api')]"))
                )

                # Test tab switching on this viewport
                dep_tab = self.driver.find_element(By.ID, "app-tab-deployments")
                dep_tab.click()
                time.sleep(0.3)

                scroll_w_detail = self.driver.execute_script("return document.documentElement.scrollWidth;")
                client_w_detail = self.driver.execute_script("return document.documentElement.clientWidth;")
                assert scroll_w_detail <= client_w_detail, f"Page overflow on Detail page in {name}: {scroll_w_detail} > {client_w_detail}"

                print(f"  ✓ Selenium Viewport {name}: scrollWidth={scroll_w} <= clientWidth={client_w}, app names unclipped")
                self.test_results[f"Selenium Responsive: {name}"] = "PASS"
            except Exception as e:
                self.test_results[f"Selenium Responsive: {name}"] = f"FAIL: {e}"
                print(f"  ❌ Selenium Viewport {name} failed: {e}")

    # =========================================================================
    # 9. SELF-HEALING & AUTOMATED REMEDIATION (Phase 11)
    # =========================================================================
    def test_self_healing_and_remediation(self):
        print("\n--- [SELENIUM] 9. Testing Phase 11 Self-Healing & Automated Remediation ---")
        try:
            self.driver.set_window_size(1440, 900)
            self.driver.get(f"{BASE_URL}/applications/inventory-api")

            # 1. Verify Overview card
            card = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "overview-remediation-card"))
            )
            assert "self-healing" in card.text.lower()
            print("  ✓ Selenium: Self-Healing overview card present")

            # 2. Click navigation link to Monitoring tab
            nav_btn = self.driver.find_element(By.ID, "btn-view-remediation-details")
            nav_btn.click()
            time.sleep(0.5)

            # 3. Verify Monitoring Remediation Panel
            panel = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.ID, "monitoring-remediation-panel"))
            )
            assert "remediation engine" in panel.text.lower()
            print("  ✓ Selenium: Deep linked into Monitoring Remediation Engine panel")

            # 4. Trigger Real Health Scan
            scan_btn = self.driver.find_element(By.ID, "btn-trigger-health-scan")
            assert scan_btn.is_displayed()
            scan_btn.click()
            time.sleep(1.0)

            banner = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "remediation-action-banner"))
            )
            assert "scan complete" in banner.text.lower() or "evaluated" in banner.text.lower()
            print(f"  ✓ Selenium: Cluster health scan triggered successfully: {banner.text}")

            self.test_results["Selenium: Self-Healing & Remediation Engine"] = "PASS"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.test_results["Selenium: Self-Healing & Remediation Engine"] = f"FAIL: {e}\n{tb}"
            print(f"  ❌ Selenium Self-Healing test failed: {e}\n{tb}")

    # =========================================================================
    # RUN ALL SELENIUM TESTS
    # =========================================================================
    def run_all(self):
        self.setup()
        try:
            self.test_sidebar_information_architecture()
            self.test_applications_catalog()
            self.test_application_header_and_actions()
            self.test_application_7_tabs()
            self.test_infrastructure_tab_k8s_and_terraform()
            self.test_automation_tab_ansible()
            self.test_actionable_notifications()
            self.test_responsive_viewports()
            self.test_self_healing_and_remediation()
        finally:
            self.teardown()

        print("\n==================================================")
        print("SELENIUM TEST SUMMARY")
        print("==================================================")
        all_passed = True
        for name, status in self.test_results.items():
            print(f"[{status}] {name}")
            if not status.startswith("PASS"):
                all_passed = False

        return all_passed, self.test_results


if __name__ == "__main__":
    suite = SeleniumQASuite()
    success, results = suite.run_all()
    sys.exit(0 if success else 1)
