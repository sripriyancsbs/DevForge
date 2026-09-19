import sys
import time
from typing import Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
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
    # 1. NAVIGATION & APP BAR VERIFICATION
    # =========================================================================
    def test_navigation(self):
        print("\n--- [SELENIUM] Testing Application Navigation ---")
        try:
            self.driver.get(BASE_URL)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DevForge')]"))
            )
            print("  ✓ DevForge loaded successfully in Selenium")

            # Click through navigation tabs
            nav_tabs = ["Applications", "Deployments", "Environments", "Infrastructure", "Monitoring", "Activity", "Settings", "Overview"]
            for tab in nav_tabs:
                elem = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//aside//button[contains(., '{tab}')]"))
                )
                elem.click()
                time.sleep(0.3)
                print(f"  ✓ Navigated to {tab}")

            self.test_results["Selenium: Navigation"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Navigation"] = f"FAIL: {e}"
            print(f"  ❌ Navigation test failed: {e}")

    # =========================================================================
    # 2. FORM VALIDATION (EMPTY, INVALID RFC 1123, SLUGIFICATION)
    # =========================================================================
    def test_form_validation(self):
        print("\n--- [SELENIUM] Testing Form Validation ---")
        try:
            self.driver.get(f"{BASE_URL}/create-application")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Create Application')]"))
            )

            # Test 1: Empty application name -> Next button is disabled
            next_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Next: Runtime & Template')]")
            assert not next_btn.is_enabled(), "Next button should be disabled when application name is empty"
            print("  ✓ Empty application name validation caught (Next button disabled)")

            # Test 2: Auto-slugification and RFC 1123 formatting
            name_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'order-processing-service')]")
            name_input.clear()
            name_input.send_keys("My Invalid App Name 123!")
            val = name_input.get_attribute("value")
            assert " " not in val and "!" not in val, f"Name not slugified: {val}"
            assert val == "my-invalid-app-name-123-", f"Unexpected slug format: {val}"
            print(f"  ✓ Input automatically sanitized to RFC 1123 DNS slug: {val}")

            self.test_results["Selenium: Form Validation"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Form Validation"] = f"FAIL: {e}"
            print(f"  ❌ Form validation failed: {e}")

    # =========================================================================
    # 3. PROVISIONING & GITHUB METADATA FLOW
    # =========================================================================
    def test_provisioning_workflow(self):
        run_suffix = int(time.time()) % 100000
        app_name = f"qa-sel-py-{run_suffix}"
        print(f"\n--- [SELENIUM] Testing Provisioning Workflow: {app_name} ---")
        try:
            self.driver.get(f"{BASE_URL}/create-application")
            name_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'order-processing-service')]"))
            )
            name_input.clear()
            name_input.send_keys(app_name)

            # Click Next: Runtime & Template
            next1 = self.driver.find_element(By.XPATH, "//button[contains(., 'Next: Runtime & Template')]")
            next1.click()
            time.sleep(0.5)

            # Click Next: Environment & Config
            next2 = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Next: Environment & Config')]"))
            )
            next2.click()
            time.sleep(0.5)

            # Submit Provisioning
            submit_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Provision Application')]"))
            )
            submit_btn.click()
            print("  ✓ Provisioning submitted")

            # Verify Stepper appears
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Provisioning Application')]"))
            )
            print("  ✓ Real-time provisioning stepper active")

            # Wait for completion (max 60 seconds)
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Application successfully generated and registered in PostgreSQL')]"))
            )
            print("  ✓ Provisioning completed successfully (READY)")

            # Check GitHub Repository link on success screen
            repo_link = self.driver.find_element(By.XPATH, "//a[contains(., 'Open Repository')]")
            href = repo_link.get_attribute("href")
            assert f"sripriyancsbs/{app_name}" in href, f"Repository URL mismatch: {href}"
            print(f"  ✓ GitHub Repository link verified in Selenium: {href}")

            # Open Application Details
            self.driver.find_element(By.XPATH, "//button[contains(., 'Open Application')]").click()
            time.sleep(1)

            # Verify Drawer contains Repository details
            drawer_repo = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, f"//h2[contains(text(), '{app_name}')]"))
            )
            assert drawer_repo.is_displayed(), "Application details drawer missing"
            print("  ✓ Application Details drawer displays application metadata")

            # Verify CI Automation section in drawer
            ci_elem = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CI Automation')]"))
            )
            assert ci_elem.is_displayed(), "Application details drawer missing CI Automation section"
            print("  ✓ Application Details drawer displays CI Automation section in Selenium")

            # Verify CI Refresh button by ID
            refresh_btn = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "refresh-ci-btn"))
            )
            assert refresh_btn.is_displayed(), "Refresh CI button missing"
            refresh_btn.click()
            time.sleep(1)
            print("  ✓ CI status refreshed via button in Selenium")

            # Verify GitHub Actions Link
            gh_actions_link = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "view-github-actions-link"))
            )
            assert gh_actions_link.is_displayed(), "View GitHub Actions link missing"
            actions_url = gh_actions_link.get_attribute("href")
            assert "github.com" in actions_url and "actions" in actions_url, f"Invalid actions URL: {actions_url}"
            print(f"  ✓ Verified GitHub Actions link in Selenium: {actions_url}")

            # Verify Phase 5 Container Image Section in drawer
            img_sec = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "app-detail-container-image-section"))
            )
            assert img_sec.is_displayed(), "Container Image section missing in drawer"
            print("  ✓ Application Details drawer displays Container Image (GHCR) section in Selenium")

            # Verify Container Image Repository
            repo_box = self.driver.find_element(By.ID, "container-image-repo")
            assert repo_box.is_displayed(), "Container image repo element missing"
            print(f"  ✓ Image repository text verified: {repo_box.text}")

            # Verify Copy Button and Click
            copy_btn = self.driver.find_element(By.ID, "copy-image-ref-btn")
            assert copy_btn.is_displayed(), "Copy image button missing"
            copy_btn.click()
            time.sleep(0.3)
            assert "Copied!" in copy_btn.text, f"Copy button text did not change to Copied!, was: {copy_btn.text}"
            print("  ✓ Copy container image reference button verified in Selenium")

            # Verify Sync Button
            sync_btn = self.driver.find_element(By.ID, "refresh-image-btn")
            assert sync_btn.is_displayed(), "Sync image button missing"
            sync_btn.click()
            time.sleep(0.5)
            print("  ✓ Container image sync button verified in Selenium")

            self.test_results["Selenium: Provisioning Workflow"] = "PASS"
        except Exception as e:
            self.test_results["Selenium: Provisioning Workflow"] = f"FAIL: {e}"
            print(f"  ❌ Provisioning workflow failed: {e}")

    # =========================================================================
    # 4. RESPONSIVE VIEWPORT TESTING (SELENIUM)
    # =========================================================================
    def test_responsive_viewports(self):
        print("\n--- [SELENIUM] Testing Responsive Viewports ---")
        viewports = [
            ("Desktop 1920x1080", 1920, 1080),
            ("Tablet 768x1024", 768, 1024),
            ("Mobile 390x844", 390, 844)
        ]
        for name, width, height in viewports:
            try:
                self.driver.set_window_size(width, height)
                self.driver.get(f"{BASE_URL}/")
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DevForge')]"))
                )
                print(f"  ✓ Selenium Viewport {name} rendered successfully")
                self.test_results[f"Selenium Responsive: {name}"] = "PASS"
            except Exception as e:
                self.test_results[f"Selenium Responsive: {name}"] = f"FAIL: {e}"
                print(f"  ❌ Selenium Viewport {name} failed: {e}")

    # =========================================================================
    # 5. RUN ALL SELENIUM TESTS
    # =========================================================================
    def run_all(self):
        self.setup()
        try:
            self.test_navigation()
            self.test_form_validation()
            self.test_provisioning_workflow()
            self.test_responsive_viewports()
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
