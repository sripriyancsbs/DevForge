import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

client = TestClient(app)

def test_login_with_valid_credentials():
    # Admin login
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@devforge.internal",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["email"] == "admin@devforge.internal"

def test_login_with_username():
    res = client.post("/api/v1/auth/login", json={
        "username": "developer",
        "password": "DeveloperPassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "DEVELOPER"

def test_login_with_invalid_credentials():
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@devforge.internal",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_signup_creates_safe_non_admin_role():
    test_email = "newuser_test_unique@devforge.internal"
    # Ensure clean state if exists
    db = SessionLocal()
    existing = db.query(User).filter(User.email == test_email).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    res = client.post("/api/v1/auth/signup", json={
        "name": "Jane Developer",
        "email": test_email,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    # Verified: Initial role is DEVELOPER, NEVER ADMIN
    assert data["user"]["role"] == "DEVELOPER"
    assert data["user"]["role"] != "ADMIN"
    assert data["user"]["email"] == test_email

def test_signup_duplicate_email_fails():
    res = client.post("/api/v1/auth/signup", json={
        "name": "Admin Impersonator",
        "email": "admin@devforge.internal",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

def test_signup_password_mismatch_fails():
    res = client.post("/api/v1/auth/signup", json={
        "name": "Mismatch User",
        "email": "mismatch@devforge.internal",
        "password": "Password123!",
        "confirm_password": "DifferentPassword123!"
    })
    assert res.status_code == 400
    assert "Passwords do not match" in res.json()["detail"]

def test_logout_endpoint():
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_protected_route_without_token():
    # Direct access to protected endpoints without header must return 401 Unauthorized
    res_me = client.get("/api/v1/auth/me")
    assert res_me.status_code == 401
    assert "not provided" in res_me.json()["detail"].lower() or "unauthorized" in res_me.json()["detail"].lower()

    res_ws = client.get("/api/v1/workspaces")
    assert res_ws.status_code == 401
