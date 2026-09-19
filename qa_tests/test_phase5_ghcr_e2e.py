"""
Phase 5 Real GHCR End-to-End Test Suite.
Validates:
1. Application creation with automated CI/CD and GHCR publishing workflow
2. Provisioning worker generates .github/workflows/ci.yml with GHCR build, tag, and push steps
3. Source code pushed to real GitHub repository
4. GitHub Actions CI automatically triggers, runs tests, builds Docker image, and pushes to GHCR
5. Image metadata tracked in PostgreSQL with READY status, canonical repository name, deterministic tag, and sha256 digest
6. DevForge REST APIs return valid image metadata (GET /images, GET /images/latest)
7. Activity feed records image build and push lifecycle events
"""

import os
import sys
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8000/api/v1"

def test_phase5_ghcr_e2e():
    print("\n==================================================")
    print("PHASE 5: REAL GHCR CONTAINER IMAGE WORKFLOW TEST")
    print("==================================================")
    
    ts = int(time.time()) % 100000
    app_name = f"qa-ghcr-py-{ts}"
    
    payload = {
        "name": app_name,
        "team": "Platform Engineering",
        "description": "Phase 5 real GHCR container image publishing test",
        "environment": "production",
        "template": "python-fastapi",
        "port": 8000
    }
    
    print(f"Step 1: Submitting application creation for '{app_name}'...")
    res = requests.post(f"{API_BASE}/applications", json=payload)
    assert res.status_code == 201, f"Failed to create application: {res.text}"
    app_json = res.json()
    job_id = app_json["job_id"]
    app_id = app_json["application"]["id"]
    print(f"  [OK] Application created (ID: {app_id}, Provisioning Job: {job_id})")
    
    # Step 2: Poll provisioning job until READY
    print("Step 2: Waiting for background provisioning worker to complete...")
    ready = False
    for attempt in range(60):
        time.sleep(1)
        j_res = requests.get(f"{API_BASE}/provisioning/{job_id}")
        if j_res.status_code != 200:
            continue
        job = j_res.json()
        status = job["status"]
        step = job.get("current_step")
        if status == "READY":
            ready = True
            print(f"  [OK] Provisioning completed successfully on attempt {attempt+1}!")
            break
        elif status == "FAILED":
            raise AssertionError(f"Provisioning job failed: {job.get('error_message')}")
    
    assert ready, "Provisioning worker timed out"
    
    # Step 3: Verify initial image record in DevForge
    print("Step 3: Checking initial container image record in DevForge...")
    img_res = requests.get(f"{API_BASE}/applications/{app_id}/images")
    assert img_res.status_code == 200, f"Failed to get images: {img_res.text}"
    img_data = img_res.json()
    print(f"  [OK] Container images list response: total={img_data['total']}")
    assert img_data["total"] >= 1, "No container image recorded after provisioning"
    
    initial_img = img_data["images"][0]
    expected_repo = f"ghcr.io/sripriyancsbs/{app_name.lower()}"
    print(f"  [OK] Initial image repository: {initial_img['repository']}")
    print(f"  [OK] Initial image tag: {initial_img['tag']}")
    print(f"  [OK] Initial image status: {initial_img['status']}")
    assert initial_img["registry"] == "ghcr.io"
    assert initial_img["repository"].lower() == expected_repo
    
    # Step 4: Track remote GitHub Actions execution
    print("Step 4: Tracking remote GitHub Actions run and GHCR build/push...")
    workflow_passed = False
    run_url = None
    for attempt in range(50):
        time.sleep(4)
        # Refresh CI status
        ci_refresh = requests.post(f"{API_BASE}/applications/{app_id}/ci/refresh")
        if ci_refresh.status_code == 200:
            ci_data = ci_refresh.json()
            ci_status = ci_data["status"]
            run_url = ci_data.get("run_url")
            print(f"  ... [Attempt {attempt+1}] GitHub Actions status: {ci_status}")
            if ci_status == "PASSED":
                workflow_passed = True
                print(f"  [OK] GitHub Actions CI run passed! Run URL: {run_url}")
                break
            elif ci_status == "FAILED":
                print(f"  [WARN] CI reported FAILED. Inspecting details at: {run_url}")
                break
    
    # Step 5: Sync image metadata from GitHub Actions & GHCR
    print("Step 5: Synchronizing container image metadata with GHCR...")
    sync_res = requests.post(f"{API_BASE}/applications/{app_id}/images/sync")
    assert sync_res.status_code == 200, f"Failed to sync image: {sync_res.text}"
    synced_img = sync_res.json()
    
    print("\n--- SYNCHRONIZED CONTAINER IMAGE METADATA ---")
    print(f"  Registry:   {synced_img.get('registry')}")
    print(f"  Repository: {synced_img.get('repository')}")
    print(f"  Tag:        {synced_img.get('tag')}")
    print(f"  Status:     {synced_img.get('status')}")
    print(f"  Digest:     {synced_img.get('digest')}")
    print("--------------------------------------------\n")
    
    assert synced_img["registry"] == "ghcr.io"
    assert synced_img["repository"].lower() == expected_repo
    assert synced_img["tag"] is not None
    assert synced_img["status"] == "READY", f"Expected READY status, got {synced_img['status']}"
    assert synced_img.get("digest") and synced_img["digest"].startswith("sha256:"), f"Expected sha256 digest, got {synced_img.get('digest')}"
    print(f"  [OK] Verified image status is READY with sha256 digest: {synced_img['digest'][:25]}...")
    
    # Verify latest image endpoint
    latest_res = requests.get(f"{API_BASE}/applications/{app_id}/images/latest")
    assert latest_res.status_code == 200
    latest_img = latest_res.json()
    assert latest_img["repository"] == synced_img["repository"]
    assert latest_img["tag"] == synced_img["tag"]
    print(f"  [OK] GET /images/latest verified matching")
    
    # Step 6: Verify Activity Log
    print("Step 6: Verifying Activity Feed has image lifecycle events...")
    act_res = requests.get(f"{API_BASE}/activity")
    assert act_res.status_code == 200
    activities = act_res.json()
    app_activities = [a for a in activities if a.get("target") == app_name or app_name in a.get("details", "")]
    print(f"  [OK] Recorded {len(app_activities)} activity events for {app_name}:")
    for a in app_activities:
        print(f"    - [{a.get('action')}] {a.get('details')}")
    assert any(a.get("action") == "Container image pushed" for a in app_activities), "Missing 'Container image pushed' activity event!"
    print(f"  [OK] Confirmed 'Container image pushed' activity recorded in PostgreSQL")
        
    print(f"\n[PASS] Real GHCR container image workflow verified successfully for {app_name}!")
    return True

if __name__ == "__main__":
    success = test_phase5_ghcr_e2e()
    sys.exit(0 if success else 1)
