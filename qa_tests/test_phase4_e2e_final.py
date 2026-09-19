import sys
import time
import requests
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:3000"
API_URL = "http://127.0.0.1:8000/api/v1"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def run_final_e2e():
    print("\n==================================================")
    print("PHASE 4 FINAL END-TO-END WORKFLOW VERIFICATION")
    print("==================================================")
    
    ts = int(time.time()) % 100000
    app_name = f"devforge-final-ci-{ts}"
    print(f"Step 1: Launching Browser to create application '{app_name}'")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 1. Navigate to Create Application
        page.goto(f"{BASE_URL}/create-application", wait_until="networkidle")
        print("  ✓ Opened Create Application page in Browser")
        
        # 2. Fill Name & Team
        name_input = page.locator("input[placeholder*='order-processing-service']")
        name_input.fill(app_name)
        page.locator("button:has-text('Next: Runtime & Template')").first.click()
        page.wait_for_timeout(400)
        
        # 3. Select Python FastAPI Template
        page.locator("div:has-text('Python FastAPI')").last.click()
        page.locator("button:has-text('Next: Environment & Config')").first.click()
        page.wait_for_timeout(400)
        
        # 4. Provision Application
        print("Step 2: Submitting Application creation request (DevForge -> Backend)")
        page.locator("button:has-text('Provision Application')").click()
        
        # 5. Verify Stepper with Phase 4 Generate CI workflow step
        print("Step 3: Verifying real-time provisioning state machine steps (Worker -> PostgreSQL)")
        stepper = page.locator("text=Provisioning Application").first
        stepper.wait_for(state="visible", timeout=10000)
        
        ci_step = page.locator("text=Generate CI workflow").first
        assert ci_step.is_visible(), "Generate CI workflow step missing in stepper"
        print("  ✓ Provisioning state machine includes 'Generate CI workflow'")
        
        # 6. Wait for READY state
        print("Step 4: Waiting for Git repository creation and push (Worker -> GitHub)")
        page.locator("text=Application successfully generated and registered in PostgreSQL").wait_for(state="visible", timeout=60000)
        print("  ✓ Provisioning reached READY state!")
        
        # Verify repository link on success page
        repo_link = page.locator("a:has-text('Open Repository')")
        repo_url = repo_link.get_attribute("href")
        print(f"  ✓ GitHub Repository provisioned: {repo_url}")
        
        # 7. Open Application Details Drawer
        print("Step 5: Opening Application Details drawer to monitor CI/CD Automation")
        page.locator("button:has-text('Open Application')").click()
        page.wait_for_timeout(1000)
        
        # Check CI Automation section
        ci_sec = page.locator("#app-detail-ci-section").first
        ci_sec.wait_for(state="visible", timeout=5000)
        print("  ✓ CI Automation card displayed in Application Details drawer")
        
        # 8. Poll CI Status until GitHub Actions finishes
        print("Step 6: Tracking GitHub Actions execution on remote repository...")
        app_id = None
        for _ in range(10):
            res_data = requests.get(f"{API_URL}/applications?query={app_name}").json()
            apps = res_data if isinstance(res_data, list) else res_data.get("applications", [])
            matches = [a for a in apps if a.get("name") == app_name]
            if matches:
                app_id = matches[0]["id"]
                break
            time.sleep(1)
            
        assert app_id, f"Application {app_name} not found in backend"
        
        final_status = "UNKNOWN"
        for i in range(45):
            time.sleep(3)
            # Click refresh button in browser
            page.locator("#refresh-ci-btn").click()
            page.wait_for_timeout(1000)
            
            ci_data = requests.get(f"{API_URL}/applications/{app_id}/ci").json()
            status = ci_data["status"]
            if status in ("RUNNING", "PASSED", "FAILED"):
                final_status = status
                print(f"  ... Remote GitHub Actions Status: {status} (Run #{ci_data.get('run_id')})")
                if status in ("PASSED", "FAILED"):
                    break
            elif status == "QUEUED":
                print(f"  ... Remote GitHub Actions is QUEUED (check {i+1})")
                
        print(f"Step 7: Final GitHub Actions CI Status: {final_status}")
        assert final_status == "PASSED", f"Expected CI status PASSED, got {final_status}"
        
        # 9. Verify UI updates with PASSED badge
        page.wait_for_timeout(1000)
        passed_badge = page.locator("text=PASSED").first
        assert passed_badge.is_visible(), "PASSED badge not visible in DevForge UI drawer"
        print("  ✓ DevForge UI displays verified 'PASSED' status badge!")
        
        # Verify View GitHub Actions button has run URL
        gh_btn = page.locator("#view-github-actions-link")
        gh_url = gh_btn.get_attribute("href")
        assert "actions/runs/" in gh_url, f"Unexpected GitHub Actions URL: {gh_url}"
        print(f"  ✓ Direct GitHub Actions link active: {gh_url}")
        
        browser.close()
        
    print("\n--- [PASS] Complete End-to-End Workflow Validated Successfully ---")
    return True

if __name__ == "__main__":
    ok = run_final_e2e()
    sys.exit(0 if ok else 1)
