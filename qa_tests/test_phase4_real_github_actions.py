import sys
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8000/api/v1"


def test_real_github_actions_provisioning():
    print("\n--- [PHASE 4 REAL CI/CD] Creating Application with Automated GitHub Actions ---")
    ts = int(time.time()) % 100000
    app_name = f"qa-ci-py-{ts}"

    payload = {
        "name": app_name,
        "team": "Platform Engineering",
        "description": "Phase 4 real GitHub Actions CI test application",
        "environment": "development",
        "template": "python-fastapi",
        "port": 8000
    }

    res = requests.post(f"{API_BASE}/applications", json=payload)
    assert res.status_code == 201, f"Failed to create app: {res.text}"
    data = res.json()
    job_id = data["job_id"]
    app_id = data["application"]["id"]
    print(f"  ✓ Application {app_name} queued (App #{app_id}, Job #{job_id})")

    # Poll provisioning job until READY
    print("  ... Waiting for provisioning worker to generate CI workflow, create repo, and push")
    ready = False
    for _ in range(60):
        time.sleep(1)
        j = requests.get(f"{API_BASE}/provisioning/{job_id}").json()
        if j["status"] == "READY":
            ready = True
            break
        elif j["status"] == "FAILED":
            raise AssertionError(f"Provisioning failed: {j.get('error_message')}")

    assert ready, f"Provisioning timed out: {j}"
    print(f"  ✓ Application reached READY state with GitHub repository provisioned")

    # Verify repository details
    app_data = requests.get(f"{API_BASE}/applications/{app_id}").json()["application"]
    repo_url = app_data["repository_url"]
    print(f"  ✓ Repository URL: {repo_url}")
    print(f"  ✓ Default Branch: {app_data['repository_default_branch']}")

    # Check manifest YAML has CI spec
    manifest_yaml = app_data.get("manifest_yaml", "")
    assert "ci:" in manifest_yaml, "devforge.yaml manifest missing CI block!"
    assert "github-actions" in manifest_yaml, "devforge.yaml manifest missing github-actions provider!"
    print("  ✓ Verified devforge.yaml specifies GitHub Actions CI automation")

    # Check CI status endpoint
    print("  ... Querying DevForge CI status API")
    ci_res = requests.get(f"{API_BASE}/applications/{app_id}/ci")
    assert ci_res.status_code == 200, f"CI status endpoint failed: {ci_res.text}"
    ci_data = ci_res.json()
    print(f"  ✓ Initial CI Status: {ci_data['status']} (workflow: {ci_data['workflow']})")

    # Poll refresh CI endpoint for GitHub Actions execution
    print("  ... Polling GitHub Actions execution via POST /api/v1/applications/{id}/ci/refresh")
    final_ci_status = ci_data["status"]
    for i in range(45):
        time.sleep(3)
        ref_res = requests.post(f"{API_BASE}/applications/{app_id}/ci/refresh")
        assert ref_res.status_code == 200, f"Refresh CI failed: {ref_res.text}"
        ref_data = ref_res.json()
        status = ref_data["status"]
        if status in ("RUNNING", "PASSED", "FAILED"):
            final_ci_status = status
            print(f"  ✓ GitHub Actions triggered on remote repository! Status: {status}")
            if ref_data.get("run_url"):
                print(f"  ✓ GitHub Actions Run URL: {ref_data['run_url']}")
            if status in ("PASSED", "FAILED"):
                break
        elif status == "QUEUED":
            final_ci_status = "QUEUED"
            print(f"  ... GitHub Actions run is QUEUED in runner queue (check {i+1})")

    print(f"  ✓ Real GitHub Actions integration verified: final status = {final_ci_status}")
    assert final_ci_status == "PASSED", f"GitHub Actions workflow did not pass (status: {final_ci_status})"
    return True


if __name__ == "__main__":
    success = test_real_github_actions_provisioning()
    print("\n==================================================")
    print("REAL GITHUB ACTIONS CI/CD VERIFICATION")
    print("==================================================")
    print(f"[PASS] Real GitHub Actions CI Provisioning: {success}")
    sys.exit(0 if success else 1)
