import os
import sys
import json
import time
import requests
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"


class SystemInternalQASuite:
    def __init__(self):
        self.test_results: Dict[str, str] = {}

    def log_result(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else f"FAIL: {detail}"
        self.test_results[name] = status
        symbol = "[PASS]" if passed else "[FAIL]"
        print(f"  {symbol} {name} {detail}")

    # =========================================================================
    # 1. API HEALTH & POSTGRESQL (NO SQLITE FALLBACK)
    # =========================================================================
    def test_health_and_postgres(self):
        print("\n--- [INTERNAL] Testing Health & PostgreSQL Strictness ---")
        try:
            res = requests.get(HEALTH_URL, timeout=5)
            assert res.status_code == 200, f"Health check failed with HTTP {res.status_code}"
            data = res.json()
            assert data.get("status") == "healthy"
            assert data.get("database") == "connected"
            assert "sqlite" not in str(data).lower(), "SQLite fallback detected!"
            self.log_result("PostgreSQL Probe & No SQLite Fallback", True)
        except Exception as e:
            self.log_result("PostgreSQL Probe & No SQLite Fallback", False, str(e))

    # =========================================================================
    # 2. API ENDPOINTS & SCHEMAS
    # =========================================================================
    def test_core_endpoints(self):
        print("\n--- [INTERNAL] Testing Core REST API Endpoints ---")
        endpoints = [
            ("/overview", 200),
            ("/applications", 200),
            ("/deployments", 200),
            ("/environments", 200),
            ("/infrastructure", 200),
            ("/monitoring", 200),
            ("/activity", 200),
            ("/integrations/github/status", 200)
        ]
        for ep, expected_status in endpoints:
            try:
                res = requests.get(f"{API_BASE}{ep}", timeout=5)
                assert res.status_code == expected_status, f"HTTP {res.status_code} != {expected_status}"
                self.log_result(f"API Endpoint: GET {ep}", True)
            except Exception as e:
                self.log_result(f"API Endpoint: GET {ep}", False, str(e))

    # =========================================================================
    # 3. GITHUB STATUS & CREDENTIAL REDACTION
    # =========================================================================
    def test_github_status_security(self):
        print("\n--- [INTERNAL] Testing GitHub Status Endpoint & Credential Leakage ---")
        try:
            res = requests.get(f"{API_BASE}/integrations/github/status", timeout=5)
            assert res.status_code == 200
            data = res.json()
            assert "owner" in data
            assert data["owner"] == "sripriyancsbs"
            assert "connected" in data

            # Verify no tokens or credentials ever returned in response object
            forbidden_keys = ["github_token", "access_token", "token", "password", "secret"]
            for k in forbidden_keys:
                assert k not in data, f"Credential key '{k}' found in response!"

            self.log_result("GitHub Status Endpoint & Redaction", True)
        except Exception as e:
            self.log_result("GitHub Status Endpoint & Redaction", False, str(e))

    # =========================================================================
    # 4. NEGATIVE TESTING & FAULT INJECTION
    # =========================================================================
    def test_negative_validations(self):
        print("\n--- [INTERNAL] Negative Testing & Validation Defenses ---")

        # 1. Empty application name
        try:
            res = requests.post(f"{API_BASE}/applications", json={"name": "", "template": "python-fastapi"})
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            self.log_result("Empty Application Name -> 422", True)
        except Exception as e:
            self.log_result("Empty Application Name -> 422", False, str(e))

        # 2. Invalid RFC 1123 name (capital letters & symbols)
        try:
            res = requests.post(f"{API_BASE}/applications", json={"name": "-invalid_Name!", "template": "python-fastapi"})
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            self.log_result("Invalid RFC 1123 DNS Name -> 422", True)
        except Exception as e:
            self.log_result("Invalid RFC 1123 DNS Name -> 422", False, str(e))

        # 3. Path traversal attack in name
        try:
            res = requests.post(f"{API_BASE}/applications", json={"name": "../../etc/passwd", "template": "python-fastapi"})
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            self.log_result("Path Traversal Attack in Name -> 422", True)
        except Exception as e:
            self.log_result("Path Traversal Attack in Name -> 422", False, str(e))

        # 4. Unsupported starter template
        try:
            res = requests.post(f"{API_BASE}/applications", json={"name": "test-invalid-tpl", "template": "ruby-on-rails"})
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            self.log_result("Unsupported Template -> 422", True)
        except Exception as e:
            self.log_result("Unsupported Template -> 422", False, str(e))

        # 5. Invalid port range (> 65535)
        try:
            res = requests.post(f"{API_BASE}/applications", json={"name": "test-invalid-port", "template": "python-fastapi", "port": 999999})
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            self.log_result("Port Out of Bounds (>65535) -> 422", True)
        except Exception as e:
            self.log_result("Port Out of Bounds (>65535) -> 422", False, str(e))

        # 6. Duplicate application collision
        try:
            app_name = "qa-collision-test-service"
            # Create first
            res1 = requests.post(f"{API_BASE}/applications", json={"name": app_name, "template": "python-fastapi"})
            if res1.status_code in (201, 409):
                # Create duplicate
                res2 = requests.post(f"{API_BASE}/applications", json={"name": app_name, "template": "python-fastapi"})
                assert res2.status_code == 409, f"Expected 409 for duplicate, got {res2.status_code}"
                self.log_result("Duplicate Application Collision -> 409", True)
            else:
                self.log_result("Duplicate Application Collision -> 409", False, f"First create failed with {res1.status_code}")
        except Exception as e:
            self.log_result("Duplicate Application Collision -> 409", False, str(e))

    # =========================================================================
    # 5. REPROVISIONING & RECOVERY
    # =========================================================================
    def test_reprovision_and_recovery(self):
        print("\n--- [INTERNAL] Testing Reprovisioning & Recovery ---")
        try:
            # Fetch an existing application
            res = requests.get(f"{API_BASE}/applications")
            apps = res.json()
            if not apps:
                print("  ⚠ No existing applications found to test reprovisioning")
                return

            target_app = apps[0]
            app_id = target_app["id"]

            # Trigger reprovisioning
            reprov_res = requests.post(f"{API_BASE}/applications/{app_id}/provision")
            assert reprov_res.status_code == 200, f"Reprovisioning failed with HTTP {reprov_res.status_code}"
            data = reprov_res.json()
            assert data["application"]["id"] == app_id
            assert "job_id" in data
            self.log_result(f"Reprovisioning Endpoint POST /applications/{app_id}/provision", True)
        except Exception as e:
            self.log_result("Reprovisioning Endpoint", False, str(e))

    def run_all(self):
        self.test_health_and_postgres()
        self.test_core_endpoints()
        self.test_github_status_security()
        self.test_negative_validations()
        self.test_reprovision_and_recovery()

        print("\n==================================================")
        print("INTERNAL ARCHITECTURE TEST SUMMARY")
        print("==================================================")
        all_passed = True
        for name, status in self.test_results.items():
            print(f"[{status}] {name}")
            if not status.startswith("PASS"):
                all_passed = False
        return all_passed, self.test_results


if __name__ == "__main__":
    suite = SystemInternalQASuite()
    success, results = suite.run_all()
    sys.exit(0 if success else 1)
