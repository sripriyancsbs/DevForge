import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.activity import Activity
from app.core.security import create_access_token, hash_password
from app.core.auth import ROLE_ADMIN, ROLE_OPERATOR, ROLE_DEVELOPER, ROLE_VIEWER

client = TestClient(app)


@pytest.fixture
def auth_tokens(db: Session):
    """Ensure baseline platform users exist in PostgreSQL and issue legitimate signed tokens."""
    roles = {
        ROLE_ADMIN: "admin",
        ROLE_OPERATOR: "operator",
        ROLE_DEVELOPER: "developer",
        ROLE_VIEWER: "viewer"
    }
    tokens = {}
    for role, username in roles.items():
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@devforge.internal",
                hashed_password=hash_password(f"{username.capitalize()}Password123!"),
                role=role,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        tokens[role] = create_access_token(
            subject=str(user.id),
            username=user.username,
            role=user.role
        )
    return tokens


# =========================================================================
# 1. Unauthenticated Requests → 401
# =========================================================================

def test_unauthenticated_request_rejected():
    """Unauthenticated requests to protected endpoints must return 401 Unauthorized."""
    # No header
    res1 = client.get("/api/v1/auth/me")
    assert res1.status_code == 401
    assert "WWW-Authenticate" in res1.headers

    # Malformed / forged token with wrong signature
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer forged.invalid.token"})
    assert res2.status_code == 401

    # Token with username not in database
    ghost_token = create_access_token(subject="999", username="ghost_user", role="ADMIN")
    res3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {ghost_token}"})
    assert res3.status_code == 401
    assert "User account not found" in res3.json()["detail"]


# =========================================================================
# 2. Four Roles & Authoritative Backend Stored Role
# =========================================================================

def test_four_roles_permissions_and_authoritative_source(auth_tokens, db: Session):
    """Verify each role returns its authoritative PostgreSQL stored role and assigned permissions."""
    expected = {
        ROLE_ADMIN: ("admin", "ADMIN"),
        ROLE_OPERATOR: ("operator", "OPERATOR"),
        ROLE_DEVELOPER: ("developer", "DEVELOPER"),
        ROLE_VIEWER: ("viewer", "VIEWER")
    }

    for role, (uname, exp_role) in expected.items():
        headers = {"Authorization": f"Bearer {auth_tokens[role]}"}
        res = client.get("/api/v1/auth/me", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == uname
        assert data["role"] == exp_role
        assert len(data["permissions"]) > 0


# =========================================================================
# 3. VIEWER attempting ADMIN-only endpoints → 403
# =========================================================================

def test_viewer_attempting_admin_endpoint_forbidden(auth_tokens):
    """VIEWER role attempting ADMIN-only endpoints must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {auth_tokens[ROLE_VIEWER]}"}

    # Attempt to create template (ADMIN only)
    res_tpl = client.post("/api/v1/templates", json={
        "id": "viewer-hack-tpl",
        "name": "Viewer Template",
        "runtime": "python",
        "framework": "fastapi"
    }, headers=headers)
    assert res_tpl.status_code == 403

    # Attempt to list all users (ADMIN only)
    res_users = client.get("/api/v1/auth/users", headers=headers)
    assert res_users.status_code == 403

    # Attempt to modify another user's role (ADMIN only)
    res_role = client.patch("/api/v1/auth/users/1/role", json={"role": "ADMIN"}, headers=headers)
    assert res_role.status_code == 403


# =========================================================================
# 4. DEVELOPER attempting ADMIN-only endpoints → 403
# =========================================================================

def test_developer_attempting_admin_endpoint_forbidden(auth_tokens):
    """DEVELOPER role attempting ADMIN-only endpoints must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {auth_tokens[ROLE_DEVELOPER]}"}

    # Attempt to create template (ADMIN only)
    res_tpl = client.post("/api/v1/templates", json={
        "id": "dev-hack-tpl",
        "name": "Dev Template",
        "runtime": "nodejs",
        "framework": "express"
    }, headers=headers)
    assert res_tpl.status_code == 403

    # Attempt to list all users (ADMIN only)
    res_users = client.get("/api/v1/auth/users", headers=headers)
    assert res_users.status_code == 403

    # Attempt to modify user role (ADMIN only)
    res_role = client.patch("/api/v1/auth/users/4/role", json={"role": "ADMIN"}, headers=headers)
    assert res_role.status_code == 403


# =========================================================================
# 5. OPERATOR attempting ADMIN-only endpoints → 403
# =========================================================================

def test_operator_attempting_admin_endpoint_forbidden(auth_tokens):
    """OPERATOR role attempting ADMIN-only endpoints must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {auth_tokens[ROLE_OPERATOR]}"}

    # Attempt to create template (ADMIN only)
    res_tpl = client.post("/api/v1/templates", json={
        "id": "op-hack-tpl",
        "name": "Op Template",
        "runtime": "go",
        "framework": "gin"
    }, headers=headers)
    assert res_tpl.status_code == 403

    # Attempt to modify user role (ADMIN only)
    res_role = client.patch("/api/v1/auth/users/4/role", json={"role": "ADMIN"}, headers=headers)
    assert res_role.status_code == 403


# =========================================================================
# 6. Forged / Manipulated Role in Client Request → Ignored / Rejected
# =========================================================================

def test_forged_or_manipulated_role_ignored_and_rejected(auth_tokens, db: Session):
    """
    Even if a client sends a token claiming 'role: ADMIN', or headers/body claiming 'ADMIN',
    the backend MUST look up the user in PostgreSQL, bind to their stored 'VIEWER' role,
    and reject privilege escalation attempts.
    """
    viewer = db.query(User).filter(User.username == "viewer").first()
    assert viewer is not None
    assert viewer.role == ROLE_VIEWER

    # Forged token claiming ADMIN for user 'viewer'
    forged_token = create_access_token(
        subject=str(viewer.id),
        username="viewer",
        role="ADMIN"  # Forged claim in token
    )

    headers = {
        "Authorization": f"Bearer {forged_token}",
        "X-DevForge-Role": "ADMIN",
        "X-Role": "ADMIN"
    }

    # Verify backend /auth/me returns the authoritative DB role 'VIEWER', not the forged 'ADMIN'
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["role"] == "VIEWER"

    # Verify accessing an ADMIN-only endpoint is rejected with 403 Forbidden
    res_admin = client.post("/api/v1/templates", json={
        "id": "forged-role-tpl",
        "name": "Forged Template",
        "runtime": "python",
        "framework": "fastapi"
    }, headers=headers)
    assert res_admin.status_code == 403


# =========================================================================
# 7. Self-Service Role Modification Rejected → 403
# =========================================================================

def test_self_service_role_modification_rejected(auth_tokens):
    """Users cannot change or promote their own role via self-service APIs."""
    for role in [ROLE_VIEWER, ROLE_DEVELOPER, ROLE_OPERATOR, ROLE_ADMIN]:
        headers = {"Authorization": f"Bearer {auth_tokens[role]}"}
        res_post = client.post("/api/v1/auth/role", json={"role": "ADMIN"}, headers=headers)
        assert res_post.status_code == 403
        assert "Self-service role modification is strictly forbidden" in res_post.json()["detail"]

        res_patch = client.patch("/api/v1/auth/role", json={"role": "ADMIN"}, headers=headers)
        assert res_patch.status_code == 403


# =========================================================================
# 8. ADMIN Performing Authorized Role Management → Allowed & Audited
# =========================================================================

def test_admin_authorized_role_management_allowed_and_audited(auth_tokens, db: Session):
    """Only an authenticated ADMIN can manage roles; changes are persisted and audited."""
    admin_headers = {"Authorization": f"Bearer {auth_tokens[ROLE_ADMIN]}"}

    # 1. Admin can list users
    res_users = client.get("/api/v1/auth/users", headers=admin_headers)
    assert res_users.status_code == 200
    users_list = res_users.json()
    assert len(users_list) >= 4

    # Locate viewer user
    viewer_user = db.query(User).filter(User.username == "viewer").first()
    assert viewer_user is not None
    original_role = viewer_user.role

    try:
        # 2. Admin promotes viewer to DEVELOPER
        res_update = client.patch(
            f"/api/v1/auth/users/{viewer_user.id}/role",
            json={"role": "DEVELOPER"},
            headers=admin_headers
        )
        assert res_update.status_code == 200
        assert res_update.json()["role"] == "DEVELOPER"

        # Verify persisted in PostgreSQL
        db.expire_all()
        reloaded = db.query(User).filter(User.id == viewer_user.id).first()
        assert reloaded.role == "DEVELOPER"

        # Verify audit activity was recorded
        audit = db.query(Activity).filter(
            Activity.target == "viewer",
            Activity.target_type == "rbac"
        ).order_by(Activity.id.desc()).first()
        assert audit is not None
        assert audit.actor == "admin"
        assert "DEVELOPER" in audit.details

        # 3. Invalid role rejected
        res_invalid = client.patch(
            f"/api/v1/auth/users/{viewer_user.id}/role",
            json={"role": "SUPER_HACKER"},
            headers=admin_headers
        )
        assert res_invalid.status_code == 400
        assert "Invalid role" in res_invalid.json()["detail"]

    finally:
        # Restore original role
        viewer_user.role = original_role
        db.commit()
