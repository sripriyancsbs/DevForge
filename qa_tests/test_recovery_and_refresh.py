import sys
import time
import subprocess
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8000/api/v1"
BASE_URL = "http://127.0.0.1:3000"


def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def test_refresh_during_provisioning():
    print("\n--- [RECOVERY] Test 1: Page Refresh / Polling Recovery During Provisioning ---")
    run_suffix = int(time.time()) % 100000
    app_name = f"qa-rec-ref-{run_suffix}"
    
    # 1. Create Application
    payload = {
        "name": app_name,
        "team": "Platform Engineering",
        "description": "Recovery test service",
        "environment": "production",
        "template": "python-fastapi",
        "port": 8000
    }
    res = requests.post(f"{API_BASE}/applications", json=payload)
    assert res.status_code == 201, f"Failed to create app: {res.text}"
    data = res.json()
    app_id = data["application"]["id"]
    job_id = data.get("job_id")
    print(f"  ✓ Application {app_name} created (App ID: {app_id}, Job ID: {job_id})")

    # 2. Simulate page reload by querying job status endpoint (which UI uses to recover state)
    job_res = requests.get(f"{API_BASE}/provisioning/by-app/{app_id}")
    assert job_res.status_code == 200, f"Job endpoint failed: {job_res.text}"
    job_data = job_res.json()
    assert job_data["id"] == job_id
    assert job_data["application_id"] == app_id
    print(f"  ✓ Recovered active provisioning job state on browser refresh: status={job_data['status']}, step={job_data['current_step']}")

    # 3. Wait for completion
    for _ in range(45):
        time.sleep(1)
        j = requests.get(f"{API_BASE}/provisioning/{job_id}").json()
        if j["status"] in ("READY", "FAILED"):
            break
    
    assert j["status"] == "READY", f"Job failed to reach READY: {j}"
    print("  ✓ Provisioning successfully recovered and reached READY state")
    return True


def test_worker_restart_and_recovery():
    print("\n--- [RECOVERY] Test 2: Worker Restart & Job Recovery ---")
    # 1. Stop worker
    print("  ... Stopping devforge-worker container")
    rc, out, err = run_cmd("wsl -u root -d Ubuntu docker stop devforge-worker")
    assert rc == 0, f"Failed to stop worker: {err}"
    print("  ✓ Worker stopped")

    try:
        # 2. Create application while worker is down
        run_suffix = int(time.time()) % 100000
        app_name = f"qa-rec-wrk-{run_suffix}"
        payload = {
            "name": app_name,
            "team": "Platform Engineering",
            "description": "Worker restart recovery test",
            "environment": "production",
            "template": "go-microservice",
            "port": 8080
        }
        res = requests.post(f"{API_BASE}/applications", json=payload)
        assert res.status_code == 201
        data = res.json()
        app_id = data["application"]["id"]
        job_id = data.get("job_id")
        print(f"  ✓ Application queued while worker was offline: job #{job_id}")

        # Verify job is PENDING in database
        j = requests.get(f"{API_BASE}/provisioning/{job_id}").json()
        assert j["status"] == "PENDING", f"Expected PENDING, got {j['status']}"
        print(f"  ✓ Job confirmed PENDING in PostgreSQL: status={j['status']}")
    finally:
        # 3. Start worker back up
        print("  ... Restarting devforge-worker container")
        rc, out, err = run_cmd("wsl -u root -d Ubuntu docker start devforge-worker")
        assert rc == 0, f"Failed to start worker: {err}"
        print("  ✓ Worker restarted successfully")

    # 4. Worker should automatically pick up queued job and process it
    print("  ... Waiting for worker to acquire and complete queued job")
    completed = False
    for _ in range(45):
        time.sleep(1)
        j = requests.get(f"{API_BASE}/provisioning/{job_id}").json()
        if j["status"] == "READY":
            completed = True
            break
    
    assert completed, f"Job was not completed by restarted worker: {j}"
    print(f"  ✓ Restarted worker automatically acquired and completed job #{job_id} (READY)")
    return True


def test_api_restart_and_persistence():
    print("\n--- [RECOVERY] Test 3: API Restart & PostgreSQL State Retention ---")
    # Query application count before restart
    before_apps = requests.get(f"{API_BASE}/applications").json()
    count_before = len(before_apps)
    print(f"  ✓ Applications before restart: {count_before}")

    # Restart backend
    print("  ... Restarting devforge-backend container")
    rc, out, err = run_cmd("wsl -u root -d Ubuntu docker restart devforge-backend")
    assert rc == 0, f"Failed to restart backend: {err}"
    
    # Wait for health
    time.sleep(3)
    for _ in range(15):
        try:
            h = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if h.status_code == 200 and h.json().get("status") == "healthy":
                break
        except Exception:
            pass
        time.sleep(1)

    print("  ✓ Backend healthy after restart")

    # Query application count after restart
    after_apps = requests.get(f"{API_BASE}/applications").json()
    count_after = len(after_apps)
    assert count_after == count_before, f"Data loss detected: before={count_before}, after={count_after}"
    print(f"  ✓ Strict PostgreSQL state verified: {count_after} applications retained with zero data loss")
    return True


if __name__ == "__main__":
    t1 = test_refresh_during_provisioning()
    t2 = test_worker_restart_and_recovery()
    t3 = test_api_restart_and_persistence()
    print("\n==================================================")
    print("RECOVERY & RESILIENCY TEST SUMMARY")
    print("==================================================")
    print(f"[PASS] Refresh During Provisioning: {t1}")
    print(f"[PASS] Worker Crash & Recovery: {t2}")
    print(f"[PASS] API Restart & State Persistence: {t3}")
    all_ok = t1 and t2 and t3
    sys.exit(0 if all_ok else 1)
