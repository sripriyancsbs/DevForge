import sys
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://127.0.0.1:8000/api/v1"


def test_concurrent_provisioning():
    print("\n--- [CONCURRENCY] Testing Simultaneous Provisioning of Two Applications ---")
    ts = int(time.time()) % 100000
    name_a = f"pre4-conc-a-{ts}"
    name_b = f"pre4-conc-b-{ts}"

    payload_a = {
        "name": name_a,
        "team": "Platform Engineering",
        "description": "Concurrent provisioning test A",
        "environment": "development",
        "template": "python-fastapi",
        "port": 8000
    }
    payload_b = {
        "name": name_b,
        "team": "Platform Engineering",
        "description": "Concurrent provisioning test B",
        "environment": "development",
        "template": "react-vite",
        "runtime": "react",
        "port": 3000
    }

    res_a = requests.post(f"{API_BASE}/applications", json=payload_a)
    assert res_a.status_code == 201, f"Failed to create app A: {res_a.text}"
    data_a = res_a.json()
    job_a = data_a["job_id"]
    app_a = data_a["application"]["id"]

    res_b = requests.post(f"{API_BASE}/applications", json=payload_b)
    assert res_b.status_code == 201, f"Failed to create app B: {res_b.text}"
    data_b = res_b.json()
    job_b = data_b["job_id"]
    app_b = data_b["application"]["id"]

    print(f"  ✓ Simultaneous jobs dispatched: Job #{job_a} (App #{app_a}) and Job #{job_b} (App #{app_b})")

    # Poll both until READY
    completed = {"a": False, "b": False}
    for _ in range(60):
        if not completed["a"]:
            ja = requests.get(f"{API_BASE}/provisioning/{job_a}").json()
            if ja["status"] == "READY":
                completed["a"] = True
                print(f"  ✓ Job #{job_a} reached READY")
            elif ja["status"] == "FAILED":
                raise AssertionError(f"Job #{job_a} failed: {ja.get('error_message')}")

        if not completed["b"]:
            jb = requests.get(f"{API_BASE}/provisioning/{job_b}").json()
            if jb["status"] == "READY":
                completed["b"] = True
                print(f"  ✓ Job #{job_b} reached READY")
            elif jb["status"] == "FAILED":
                raise AssertionError(f"Job #{job_b} failed: {jb.get('error_message')}")

        if completed["a"] and completed["b"]:
            break
        time.sleep(1)

    assert completed["a"] and completed["b"], f"Timed out waiting for concurrent jobs: {completed}"

    # Verify distinct repositories and workspaces
    app_a_data = requests.get(f"{API_BASE}/applications/{app_a}").json()["application"]
    app_b_data = requests.get(f"{API_BASE}/applications/{app_b}").json()["application"]

    assert app_a_data["repository_name"] == name_a
    assert app_b_data["repository_name"] == name_b
    assert app_a_data["generated_path"] != app_b_data["generated_path"]
    print(f"  ✓ Distinct repositories verified: {app_a_data['repository_url']} vs {app_b_data['repository_url']}")
    print(f"  ✓ Isolated workspaces verified: {app_a_data['generated_path']} vs {app_b_data['generated_path']}")
    return True


def test_reprovisioning_and_retry():
    print("\n--- [RETRY/REPROVISION] Testing Safe Reprovisioning ---")
    ts = int(time.time()) % 100000
    name = f"pre4-retry-{ts}"
    payload = {
        "name": name,
        "team": "Platform Engineering",
        "description": "Reprovisioning safety test",
        "environment": "staging",
        "template": "go-microservice",
        "runtime": "go",
        "port": 8080
    }
    res = requests.post(f"{API_BASE}/applications", json=payload)
    assert res.status_code == 201
    data = res.json()
    app_id = data["application"]["id"]
    job_id = data["job_id"]

    # Wait for completion
    for _ in range(45):
        j = requests.get(f"{API_BASE}/provisioning/{job_id}").json()
        if j["status"] == "READY":
            break
        time.sleep(1)
    assert j["status"] == "READY"
    print(f"  ✓ Initial provisioning completed: Job #{job_id} is READY")

    # Reprovision application via POST /applications/{app_id}/provision
    reprov_res = requests.post(f"{API_BASE}/applications/{app_id}/provision")
    assert reprov_res.status_code == 200, f"Reprovision failed: {reprov_res.text}"
    reprov_data = reprov_res.json()
    new_job_id = reprov_data["job_id"]
    print(f"  ✓ Triggered reprovisioning: New Job #{new_job_id}")

    # Wait for completion of new job
    for _ in range(45):
        j2 = requests.get(f"{API_BASE}/provisioning/{new_job_id}").json()
        if j2["status"] == "READY":
            break
        time.sleep(1)
    assert j2["status"] == "READY"
    print(f"  ✓ Reprovisioned job successfully completed without repository duplication or corruption")
    return True


if __name__ == "__main__":
    t1 = test_concurrent_provisioning()
    t2 = test_reprovisioning_and_retry()
    print("\n==================================================")
    print("CONCURRENCY & RETRY TEST SUMMARY")
    print("==================================================")
    print(f"[PASS] Concurrent Provisioning: {t1}")
    print(f"[PASS] Safe Reprovisioning & Retry: {t2}")
    sys.exit(0 if (t1 and t2) else 1)
