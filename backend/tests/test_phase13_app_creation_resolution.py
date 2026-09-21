import os
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.application import Application
from app.models.provisioning_job import ProvisioningJob
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.core.security import create_access_token


@pytest.fixture
def test_client():
    return TestClient(app)


def test_1_to_8_application_creation_and_resolution_lifecycle(test_client, db):
    """
    Targeted test covering requirements 1 through 8:
    1. Create application
    2. Verify transaction committed
    3. Verify application record exists
    4. Verify provisioning job exists
    5. Verify application detail endpoint immediately resolves the application
    6. Verify application can be resolved while provisioning is pending
    7. Verify workspace authorization
    8. Verify invalid application still returns true not-found behavior
    """
    app_name = f"order-processing-{os.getpid()}"

    # Ensure clean state
    existing = db.query(Application).filter(Application.name == app_name).first()
    if existing:
        db.delete(existing)
        db.commit()

    # Authenticate as admin via standard JWT
    admin_user = db.query(User).filter(User.username == "admin").first()
    assert admin_user is not None
    admin_token = create_access_token(str(admin_user.id), admin_user.username, admin_user.role)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create application 'order-processing'
    payload = {
        "name": app_name,
        "team": "Platform Engineering",
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000,
        "replicas": 1
    }
    create_res = test_client.post("/api/v1/applications", json=payload, headers=headers)
    assert create_res.status_code == 201, f"Failed creation: {create_res.text}"
    create_data = create_res.json()
    assert create_data["application"]["name"] == app_name
    canonical_name = create_data["application"]["name"]
    canonical_slug = create_data["application"]["slug"]
    job_id = create_data["job_id"]
    assert job_id is not None

    # 2. Verify transaction committed
    # Re-query in fresh transaction/session
    db.expire_all()

    # 3. Verify application record exists in PostgreSQL
    db_app = db.query(Application).filter(Application.name == app_name).first()
    assert db_app is not None
    assert db_app.name == app_name
    assert db_app.slug == canonical_slug
    assert db_app.provisioning_status in ["PENDING", "PROVISIONING", "READY"]

    # 4. Verify provisioning job exists in PostgreSQL
    db_job = db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()
    assert db_job is not None
    assert db_job.application_id == db_app.id

    # 5. Verify application detail endpoint immediately resolves the application by slug and by name
    res_slug = test_client.get(f"/api/v1/applications/{canonical_slug}", headers=headers)
    assert res_slug.status_code == 200
    slug_data = res_slug.json()
    assert slug_data["application"]["name"] == app_name
    assert slug_data["provisioning_job"] is not None
    assert slug_data["provisioning_job"]["id"] == job_id

    res_name = test_client.get(f"/api/v1/applications/{canonical_name}", headers=headers)
    assert res_name.status_code == 200
    assert res_name.json()["application"]["slug"] == canonical_slug

    # Also verify deterministic session token works identically
    res_session = test_client.get(f"/api/v1/applications/{canonical_name}", headers={"Authorization": "Bearer df_session_token_admin"})
    assert res_session.status_code == 200

    # 6. Verify application can be resolved while provisioning is pending
    # Explicitly set job & app to PENDING in database to test pending state discovery
    db_app.provisioning_status = "PENDING"
    db_app.status = "pending"
    db.commit()

    res_pending = test_client.get(f"/api/v1/applications/{canonical_name}", headers=headers)
    assert res_pending.status_code == 200
    assert res_pending.json()["application"]["provisioning_status"] == "PENDING"
    assert res_pending.json()["application"]["status"] == "pending"

    # Also verify it appears in list_applications while pending
    res_list = test_client.get("/api/v1/applications", headers=headers)
    assert res_list.status_code == 200
    app_names = [a["name"] for a in res_list.json()]
    assert app_name in app_names

    # 7. Verify workspace authorization:
    # A user from an isolated workspace (who does NOT belong to default-workspace) should get 403
    isolated_ws = db.query(Workspace).filter(Workspace.slug == "isolated-workspace").first()
    if not isolated_ws:
        isolated_ws = Workspace(name="Isolated Workspace", slug="isolated-workspace", status="active")
        db.add(isolated_ws)
        db.commit()
        db.refresh(isolated_ws)

    isolated_user = db.query(User).filter(User.username == "isolated_qa_user").first()
    if not isolated_user:
        isolated_user = User(username="isolated_qa_user", email="isolated@devforge.internal", role="DEVELOPER", is_active=True, hashed_password="mock_hashed_password")
        db.add(isolated_user)
        db.commit()
        db.refresh(isolated_user)

    # Ensure isolated_user is ONLY member of isolated_ws
    existing_mem = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == isolated_user.id).all()
    for em in existing_mem:
        db.delete(em)
    db.commit()

    db.add(WorkspaceMember(workspace_id=isolated_ws.id, user_id=isolated_user.id, role="DEVELOPER", status="active"))
    db.commit()

    iso_token = create_access_token(str(isolated_user.id), isolated_user.username, isolated_user.role)
    res_unauth = test_client.get(f"/api/v1/applications/{canonical_name}", headers={"Authorization": f"Bearer {iso_token}"})
    assert res_unauth.status_code == 403
    assert "Forbidden" in res_unauth.json().get("detail", "")

    # 8. Verify invalid application still returns true not-found behavior (404)
    res_invalid = test_client.get("/api/v1/applications/non-existent-app-xyz-99999", headers=headers)
    assert res_invalid.status_code == 404
    assert "not found" in res_invalid.json().get("detail", "").lower()
