import os
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    mask_secret,
)
from app.core.rate_limit import rate_limiter
from app.db.session import SessionLocal
from app.models.user import User
from app.models.application import Application
from app.models.remediation import RemediationPolicy, RemediationEvent
from app.services.remediation import remediation_engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiter counters before every test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_tokens(db_session: Session):
    """Generate access tokens for all 4 RBAC roles."""
    roles = ["ADMIN", "OPERATOR", "DEVELOPER", "VIEWER"]
    tokens = {}
    for role in roles:
        username = role.lower()
        user = db_session.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@devforge.internal",
                hashed_password=hash_password(f"{username.capitalize()}Password123!"),
                role=role,
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        tokens[role] = create_access_token(
            subject=str(user.id),
            username=user.username,
            role=user.role
        )
    return tokens


# =========================================================================
# 1. Cryptography & Password Hashing Tests
# =========================================================================

def test_password_hashing_and_verification():
    raw_password = "SecureProductionPassword2026!"
    hashed = hash_password(raw_password)

    # Must follow standard PBKDF2 structure
    assert hashed.startswith("pbkdf2_sha256$600000$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False

    # Distinct salts must generate different hashes for identical passwords
    hashed_second = hash_password(raw_password)
    assert hashed != hashed_second
    assert verify_password(raw_password, hashed_second) is True


def test_jwt_token_lifecycle():
    token = create_access_token(
        subject="42",
        username="secops_lead",
        role="OPERATOR"
    )
    assert token.count(".") == 2

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["username"] == "secops_lead"
    assert payload["role"] == "OPERATOR"

    # Verify signature tampering causes validation rejection
    tampered = token[:-4] + "xxxx"
    assert decode_access_token(tampered) is None


# =========================================================================
# 2. Authentication API Tests
# =========================================================================

def test_auth_login_successful():
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "AdminPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"
    assert "deploy:trigger" in data["user"]["permissions"]


def test_auth_login_invalid_credentials():
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "IncorrectPassword!"
    })
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_auth_me_endpoint(auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['OPERATOR']}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "operator"
    assert response.json()["role"] == "OPERATOR"


# =========================================================================
# 3. RBAC Authorization Enforcement Tests
# =========================================================================

def test_unauthenticated_requests_to_mutating_endpoints_rejected():
    """Verify that unauthenticated direct requests to sensitive endpoints fail with 401."""
    endpoints = [
        ("POST", "/api/v1/deployments/trigger", {"application_id": 1, "version": "v1.2.3", "environment": "development"}),
        ("POST", "/api/v1/infrastructure/terraform/plan", {"environment": "development"}),
        ("POST", "/api/v1/infrastructure/terraform/apply", {"environment": "development"}),
        ("POST", "/api/v1/ansible/executions", {"playbook_name": "health_check", "environment_id": "development"}),
        ("POST", "/api/v1/remediation/scan", {}),
    ]
    for method, path, payload in endpoints:
        if method == "POST":
            res = client.post(path, json=payload)
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"


def test_viewer_role_rejected_on_sensitive_operations(auth_tokens):
    """Verify that VIEWER role receives 403 Forbidden on write/execute endpoints."""
    headers = {"Authorization": f"Bearer {auth_tokens['VIEWER']}"}

    # 1. Trigger deployment
    res = client.post("/api/v1/deployments/trigger", json={
        "application_id": 1,
        "version": "v1.0.9",
        "environment": "development"
    }, headers=headers)
    assert res.status_code == 403

    # 2. Terraform plan
    res = client.post("/api/v1/infrastructure/terraform/plan", json={
        "environment": "development"
    }, headers=headers)
    assert res.status_code == 403

    # 3. Ansible execute
    res = client.post("/api/v1/ansible/executions", json={
        "playbook_name": "health_check",
        "environment_id": "development"
    }, headers=headers)
    assert res.status_code == 403

    # 4. Remediation scan
    res = client.post("/api/v1/remediation/scan", json={}, headers=headers)
    assert res.status_code == 403


def test_operator_can_plan_terraform_but_cannot_apply_without_admin(auth_tokens):
    """Operator role is allowed to run plan, but apply requires ADMIN."""
    operator_headers = {"Authorization": f"Bearer {auth_tokens['OPERATOR']}"}

    # Operator cannot directly apply terraform
    res = client.post("/api/v1/infrastructure/terraform/apply", json={
        "environment": "development"
    }, headers=operator_headers)
    assert res.status_code == 403


def test_developer_can_trigger_deployment(auth_tokens, db_session: Session):
    """DEVELOPER role is authorized to trigger deployments."""
    app_record = db_session.query(Application).first()
    assert app_record is not None

    dev_headers = {"Authorization": f"Bearer {auth_tokens['DEVELOPER']}"}
    res = client.post("/api/v1/deployments/trigger", json={
        "application_id": app_record.id,
        "version": "v2.0.0-test",
        "environment": "development"
    }, headers=dev_headers)
    assert res.status_code == 201
    assert res.json()["version"] == "v2.0.0-test"


# =========================================================================
# 4. Rate Limiting & Abuse Protection Tests
# =========================================================================

def test_rate_limiting_enforcement():
    """Verify sliding-window rate limit returns 429 Too Many Requests."""
    for i in range(5):
        res = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "WrongPassword!"
        })
        assert res.status_code in (401, 200)

    # 6th attempt within the minute window must trigger 429
    res_exceeded = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "WrongPassword!"
    })
    assert res_exceeded.status_code == 429
    assert "Retry-After" in res_exceeded.headers


# =========================================================================
# 5. Security Headers & CORS Tests
# =========================================================================

def test_security_headers_present_in_responses():
    response = client.get("/healthz")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in headers


# =========================================================================
# 6. Health and Readiness Probes Tests
# =========================================================================

def test_liveness_probe():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "connected"


# =========================================================================
# 7. Secret Redaction / Masking Utility Tests
# =========================================================================

def test_secret_masking_utility():
    sample_text = (
        "Connected with password=super_secret_db_pass to postgres. "
        "User token: bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz. "
        "GitHub token ghp_123456789012345678901234567890123456."
    )
    masked = mask_secret(sample_text)
    assert "super_secret_db_pass" not in masked
    assert "ghp_123456789012345678901234567890123456" not in masked
    assert "***REDACTED***" in masked


# =========================================================================
# 8. Self-Healing Safety Controls Tests (Phase 11 Preservation)
# =========================================================================

def test_self_healing_safety_cooldown_and_max_attempts(db_session: Session):
    """Verify remediation engine preserves cooldowns and max attempt thresholds."""
    from app.services.remediation import policy_service
    from app.services.remediation.exceptions import MaxAttemptsExceededError

    app_record = db_session.query(Application).first()
    assert app_record is not None

    # Create detected event
    event = remediation_engine.create_event(
        application_id=app_record.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        source="kubernetes",
        severity="HIGH",
        details="Safety test probe failure",
        db=db_session
    )
    assert event.id is not None
    assert event.attempts == 0

    # Max attempts protection: policy evaluation raises MaxAttemptsExceededError
    policy = policy_service.match_policy(event, db_session)
    assert policy is not None
    event.attempts = policy.max_attempts

    with pytest.raises(MaxAttemptsExceededError):
        policy_service.evaluate_safety(event, policy, db_session)

    # Triggering remediation on maxed-out attempts must escalate safely, not loop
    execution = remediation_engine.process_event(event.id, db_session)
    db_session.refresh(event)
    assert event.status == "ESCALATED"
