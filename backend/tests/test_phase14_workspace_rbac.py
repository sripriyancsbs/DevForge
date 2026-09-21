import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.application import Application
from app.models.activity import Activity
from app.core.security import create_access_token, hash_password
from app.core.auth import ROLE_ADMIN, ROLE_OPERATOR, ROLE_DEVELOPER, ROLE_VIEWER

client = TestClient(app)


@pytest.fixture
def setup_phase14_data(db: Session):
    """
    Ensure test workspaces, users, and workspace memberships exist.
    - Workspace A: 'default-workspace' (ID: resolved)
    - Workspace B: 'isolated-workspace' (ID: resolved)
    - admin: member of A (ADMIN) and B (ADMIN)
    - operator: member of A (OPERATOR)
    - developer: member of A (DEVELOPER)
    - viewer: member of A (VIEWER)
    - cross_user: member ONLY of B (DEVELOPER)
    - disabled_user: member of A (DEVELOPER), status='disabled'
    """
    # 1. Workspaces
    ws_a = db.query(Workspace).filter(Workspace.slug == "default-workspace").first()
    if not ws_a:
        ws_a = Workspace(name="Default Workspace", slug="default-workspace", description="Default test workspace", status="active")
        db.add(ws_a)
        db.commit()
        db.refresh(ws_a)

    ws_b = db.query(Workspace).filter(Workspace.slug == "isolated-workspace").first()
    if not ws_b:
        ws_b = Workspace(name="Isolated Workspace", slug="isolated-workspace", description="Isolated tenant workspace", status="active")
        db.add(ws_b)
        db.commit()
        db.refresh(ws_b)

    # 2. Users & Memberships
    users_spec = [
        ("admin", "admin@devforge.internal", ROLE_ADMIN, True, "active", [(ws_a, ROLE_ADMIN), (ws_b, ROLE_ADMIN)]),
        ("operator", "operator@devforge.internal", ROLE_OPERATOR, True, "active", [(ws_a, ROLE_OPERATOR)]),
        ("developer", "developer@devforge.internal", ROLE_DEVELOPER, True, "active", [(ws_a, ROLE_DEVELOPER)]),
        ("viewer", "viewer@devforge.internal", ROLE_VIEWER, True, "active", [(ws_a, ROLE_VIEWER)]),
        ("cross_user", "cross@devforge.internal", ROLE_DEVELOPER, True, "active", [(ws_b, ROLE_DEVELOPER)]),
        ("disabled_user", "disabled@devforge.internal", ROLE_DEVELOPER, False, "disabled", [(ws_a, ROLE_DEVELOPER)]),
    ]

    tokens = {}
    users = {}

    for username, email, global_role, is_active, status_val, memberships in users_spec:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(
                username=username,
                email=email,
                hashed_password=hash_password(f"{username.capitalize()}Password123!"),
                role=global_role,
                is_active=is_active,
                display_name=username.capitalize(),
                status=status_val
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        else:
            u.is_active = is_active
            u.status = status_val
            db.commit()
            db.refresh(u)

        users[username] = u
        tokens[username] = create_access_token(
            subject=str(u.id),
            username=u.username,
            role=u.role
        )

        # Synchronize exact workspace memberships for this user
        allowed_ws_ids = [ws.id for ws, _ in memberships]
        db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == u.id,
            ~WorkspaceMember.workspace_id.in_(allowed_ws_ids)
        ).delete(synchronize_session=False)
        db.commit()

        for ws, role in memberships:
            m = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == u.id
            ).first()
            if not m:
                m = WorkspaceMember(
                    workspace_id=ws.id,
                    user_id=u.id,
                    role=role,
                    status="active"
                )
                db.add(m)
                db.commit()
            else:
                m.role = role
                m.status = "active"
                db.commit()

    # 3. Applications in respective workspaces
    app_a = db.query(Application).filter(Application.name == "app-in-workspace-a").first()
    if not app_a:
        app_a = Application(
            name="app-in-workspace-a",
            slug="app-in-workspace-a",
            description="App belonging to Workspace A",
            repository_url="https://github.com/sripriyancsbs/app-in-workspace-a",
            environment="production",
            status="healthy",
            workspace_id=ws_a.id
        )
        db.add(app_a)
        db.commit()
    else:
        app_a.workspace_id = ws_a.id
        db.commit()

    app_b = db.query(Application).filter(Application.name == "app-in-workspace-b").first()
    if not app_b:
        app_b = Application(
            name="app-in-workspace-b",
            slug="app-in-workspace-b",
            description="App belonging to Workspace B",
            repository_url="https://github.com/sripriyancsbs/app-in-workspace-b",
            environment="production",
            status="healthy",
            workspace_id=ws_b.id
        )
        db.add(app_b)
        db.commit()
    else:
        app_b.workspace_id = ws_b.id
        db.commit()

    return {
        "ws_a": ws_a,
        "ws_b": ws_b,
        "users": users,
        "tokens": tokens,
        "app_a": app_a,
        "app_b": app_b
    }


# =========================================================================
# 1. Unauthenticated → protected endpoint → 401
# =========================================================================
def test_1_unauthenticated_protected_endpoint_401():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers

    res2 = client.get("/api/v1/workspaces")
    assert res2.status_code == 401


# =========================================================================
# 2. VIEWER → viewer action → allowed
# =========================================================================
def test_2_viewer_action_allowed(setup_phase14_data):
    token = setup_phase14_data["tokens"]["viewer"]
    res = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["role"] == ROLE_VIEWER


# =========================================================================
# 3. VIEWER → developer action → rejected
# =========================================================================
def test_3_viewer_developer_action_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["viewer"]
    payload = {
        "name": "viewer-illegal-app",
        "description": "Unauthorized creation attempt",
        "repository": "test/illegal",
        "environment": "staging",
        "template_id": "fastapi-service"
    }
    res = client.post("/api/v1/applications", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


# =========================================================================
# 4. VIEWER → operator action → rejected
# =========================================================================
def test_4_viewer_operator_action_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["viewer"]
    # Attempt remediation scan or trigger
    res = client.post("/api/v1/remediation/scan", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


# =========================================================================
# 5. VIEWER → admin action → rejected
# =========================================================================
def test_5_viewer_admin_action_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["viewer"]
    ws_id = setup_phase14_data["ws_a"].id
    # Attempt to invite/add member to workspace
    payload = {
        "user_id": 999,
        "role": "DEVELOPER"
    }
    res = client.post(f"/api/v1/workspaces/{ws_id}/members", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


# =========================================================================
# 6. DEVELOPER → admin action → rejected
# =========================================================================
def test_6_developer_admin_action_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["developer"]
    ws_id = setup_phase14_data["ws_a"].id
    # Attempt member management
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "hacker@test.com", "role": "ADMIN"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403

    # Attempt user role modification
    target_id = setup_phase14_data["users"]["viewer"].id
    res2 = client.patch(
        f"/api/v1/auth/users/{target_id}/role",
        json={"role": "ADMIN"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res2.status_code == 403


# =========================================================================
# 7. OPERATOR → admin-only action → rejected
# =========================================================================
def test_7_operator_admin_action_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["operator"]
    ws_id = setup_phase14_data["ws_a"].id
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "hacker@test.com", "role": "OPERATOR"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


# =========================================================================
# 8. ADMIN → authorized admin action → allowed
# =========================================================================
def test_8_admin_authorized_admin_action_allowed(setup_phase14_data):
    token = setup_phase14_data["tokens"]["admin"]
    ws_id = setup_phase14_data["ws_a"].id
    res = client.get(f"/api/v1/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    members = res.json()
    assert isinstance(members, list)
    assert any(m["role"] == "ADMIN" for m in members)


# =========================================================================
# 9. User from Workspace A → Workspace B application → rejected (IDOR)
# =========================================================================
def test_9_cross_workspace_application_idor_rejected(setup_phase14_data):
    """
    'viewer' belongs ONLY to Workspace A ('default-workspace').
    'app-in-workspace-b' belongs to Workspace B ('isolated-workspace').
    Attempting to view or manipulate 'app-in-workspace-b' must be rejected with 403.
    """
    token = setup_phase14_data["tokens"]["viewer"]
    app_b_name = setup_phase14_data["app_b"].name
    res = client.get(f"/api/v1/applications/{app_b_name}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")

    # Also test cross_user (only in Workspace B) attempting to access Workspace A app
    token_cross = setup_phase14_data["tokens"]["cross_user"]
    app_a_name = setup_phase14_data["app_a"].name
    res2 = client.get(f"/api/v1/applications/{app_a_name}", headers={"Authorization": f"Bearer {token_cross}"})
    assert res2.status_code == 403


# =========================================================================
# 10. Forged role in request → rejected/ignored
# =========================================================================
def test_10_forged_role_in_request_rejected_or_ignored(setup_phase14_data):
    token = setup_phase14_data["tokens"]["viewer"]
    # Send forged role headers or payload
    res = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Role": "ADMIN",
            "Role": "ADMIN",
            "X-Assumed-Role": "ADMIN"
        }
    )
    assert res.status_code == 200
    # Role remains VIEWER because database is the sole authority
    assert res.json()["role"] == "VIEWER"

    # Attempt an admin action with forged headers
    ws_id = setup_phase14_data["ws_a"].id
    res2 = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "escalated@test.com", "role": "ADMIN"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Role": "ADMIN"
        }
    )
    assert res2.status_code == 403


# =========================================================================
# 11. Self-promotion to ADMIN → rejected
# =========================================================================
def test_11_self_promotion_to_admin_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["developer"]
    # Attempt to call self-role alteration endpoints
    res1 = client.patch(
        "/api/v1/auth/role",
        json={"role": "ADMIN"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res1.status_code == 403

    res2 = client.post(
        "/api/v1/auth/role",
        json={"role": "ADMIN"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res2.status_code == 403

    # Attempt to modify own membership in workspace
    dev_id = setup_phase14_data["users"]["developer"].id
    ws_id = setup_phase14_data["ws_a"].id
    res3 = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{dev_id}",
        json={"role": "ADMIN"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res3.status_code == 403


# =========================================================================
# 12. Unauthorized role modification → rejected
# =========================================================================
def test_12_unauthorized_role_modification_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["operator"]
    viewer_id = setup_phase14_data["users"]["viewer"].id
    ws_id = setup_phase14_data["ws_a"].id

    # OPERATOR cannot change VIEWER to DEVELOPER or ADMIN
    res = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{viewer_id}",
        json={"role": "DEVELOPER"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403


# =========================================================================
# 13. Disabled user → protected resource → rejected
# =========================================================================
def test_13_disabled_user_protected_resource_rejected(setup_phase14_data):
    token = setup_phase14_data["tokens"]["disabled_user"]
    # Disabled user access token must be rejected at auth layer
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [401, 403]

    res2 = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code in [401, 403]


# =========================================================================
# Additional: Admin Member Management Full Lifecycle & Audit Logging
# =========================================================================
def test_admin_member_management_lifecycle_and_audit(setup_phase14_data, db: Session):
    token_admin = setup_phase14_data["tokens"]["admin"]
    ws_id = setup_phase14_data["ws_a"].id

    # Clean up any previous test run user
    existing_u = db.query(User).filter(User.username == "newinvitee").first()
    if existing_u:
        db.query(WorkspaceMember).filter(WorkspaceMember.user_id == existing_u.id).delete()
        db.delete(existing_u)
        db.commit()

    # 1. Add new member (with credentials creation)
    new_user_email = "newinvitee@devforge.internal"
    res_add = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={
            "email": new_user_email,
            "username": "newinvitee",
            "display_name": "New Invitee",
            "role": "DEVELOPER"
        },
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_add.status_code == 201
    member_data = res_add.json()
    assert member_data["email"] == new_user_email
    assert member_data["role"] == "DEVELOPER"
    new_member_id = member_data["id"]

    # 2. Update role from DEVELOPER to OPERATOR
    res_update = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{new_member_id}",
        json={"role": "OPERATOR"},
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_update.status_code == 200
    assert res_update.json()["role"] == "OPERATOR"

    # 3. Disable member
    res_disable = client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{new_member_id}",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_disable.status_code == 200
    assert res_disable.json()["status"] == "success"

    disabled_member = db.query(WorkspaceMember).filter(WorkspaceMember.id == new_member_id).first()
    assert disabled_member.status == "disabled"

    # 4. Verify audit activity logs exist for these security operations
    activities = db.query(Activity).filter(Activity.target_type == "workspace_membership").all()
    assert len(activities) >= 3
