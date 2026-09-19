import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.ansible_execution import AnsibleExecution
from app.models.activity import Activity
from app.services.ansible import (
    ansible_client,
    strip_ansi,
    playbook_service,
    execution_service,
    AnsibleError,
    AnsiblePlaybookNotFoundError,
    AnsibleSecurityError,
)
from app.core.security import create_access_token

admin_token = create_access_token(subject="1", username="admin", role="ADMIN")
client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})


def test_strip_ansi():
    raw = "\x1b[32mPLAY [Configure Environment]\x1b[0m \x1b[33mchanged: [devforge-local]\x1b[0m"
    clean = strip_ansi(raw)
    assert clean == "PLAY [Configure Environment] changed: [devforge-local]"
    assert strip_ansi("") == ""
    assert strip_ansi(None) == ""


def test_ansible_is_installed():
    if not ansible_client.is_installed():
        pytest.skip("Ansible CLI not installed on this test host")
    assert ansible_client.is_installed() is True
    version = ansible_client.get_version()
    assert "ansible-playbook" in version or "2." in version


def test_security_path_traversal():
    with pytest.raises(AnsibleSecurityError):
        ansible_client._resolve_safe_path("../../../etc/passwd")

    with pytest.raises(AnsibleSecurityError):
        ansible_client._resolve_safe_path("/etc/shadow")

    with pytest.raises(AnsibleSecurityError):
        ansible_client._resolve_safe_path("")


def test_playbook_service_list_playbooks():
    playbooks = playbook_service.list_playbooks()
    assert len(playbooks) >= 3
    names = [p["name"] for p in playbooks]
    assert "configure_application" in names
    assert "configure_environment" in names
    assert "health_check" in names


def test_playbook_service_validate_unknown_playbook():
    with pytest.raises(AnsiblePlaybookNotFoundError):
        playbook_service.validate_playbook("destroy_server")

    with pytest.raises(AnsiblePlaybookNotFoundError):
        playbook_service.validate_playbook("arbitrary_command")


def test_playbook_service_unsupported_environment():
    with pytest.raises(AnsibleSecurityError):
        playbook_service.resolve_inventory("invalid_env_name_123")


def test_execution_service_create_and_acquire():
    db = SessionLocal()
    try:
        # Create execution
        exec_record = execution_service.create_execution(
            db=db,
            playbook_name="health_check",
            environment_id="development"
        )
        assert exec_record.id is not None
        assert exec_record.status == "PENDING"
        assert exec_record.playbook_name == "health_check"

        # Acquire next
        acquired = execution_service.acquire_next_execution(db)
        assert acquired is not None
        assert acquired.id == exec_record.id

        # Clean up
        db.delete(exec_record)
        db.commit()
    finally:
        db.close()


def test_execution_service_execute_job_success_and_idempotency():
    if not ansible_client.is_installed():
        pytest.skip("Ansible CLI not installed on this test host")
    db = SessionLocal()
    try:
        # 1. First run of configure_environment
        exec_1 = execution_service.create_execution(
            db=db,
            playbook_name="configure_environment",
            environment_id="development"
        )
        completed_1 = execution_service.execute_job(exec_1.id, db)
        assert completed_1.status == "SUCCESS"
        assert completed_1.return_code == 0
        assert "failed=0" in completed_1.output

        # Verify activity was logged
        act = (
            db.query(Activity)
            .filter(Activity.action == "Ansible playbook completed")
            .order_by(Activity.id.desc())
            .first()
        )
        assert act is not None
        assert "configure_environment" in act.target

        # 2. Second run - idempotency check
        exec_2 = execution_service.create_execution(
            db=db,
            playbook_name="configure_environment",
            environment_id="development"
        )
        completed_2 = execution_service.execute_job(exec_2.id, db)
        assert completed_2.status == "SUCCESS"
        assert completed_2.return_code == 0
        assert "changed=0" in completed_2.output
        assert "failed=0" in completed_2.output
    finally:
        db.close()


def test_execution_service_retry():
    if not ansible_client.is_installed():
        pytest.skip("Ansible CLI not installed on this test host")
    db = SessionLocal()
    try:
        exec_rec = execution_service.create_execution(
            db=db,
            playbook_name="health_check",
            environment_id="development"
        )
        # Execute it
        execution_service.execute_job(exec_rec.id, db)
        assert exec_rec.status == "SUCCESS"

        # Retry
        retried = execution_service.retry_execution(exec_rec.id, db)
        assert retried.status == "PENDING"
        assert retried.output is None
        assert retried.return_code is None
    finally:
        db.close()


def test_api_get_playbooks():
    response = client.get("/api/v1/ansible/playbooks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    names = [p["name"] for p in data]
    assert "configure_application" in names
    assert "configure_environment" in names
    assert "health_check" in names


def test_api_create_execution_success():
    payload = {
        "playbook_name": "health_check",
        "environment_id": "development"
    }
    response = client.post("/api/v1/ansible/executions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "PENDING"
    assert data["playbook_name"] == "health_check"


def test_api_create_execution_invalid_playbook():
    payload = {
        "playbook_name": "arbitrary_unauthorized_playbook",
        "environment_id": "development"
    }
    response = client.post("/api/v1/ansible/executions", json=payload)
    assert response.status_code == 400
    assert "not an approved playbook" in response.json()["detail"]


def test_api_create_execution_invalid_environment():
    payload = {
        "playbook_name": "health_check",
        "environment_id": "unsupported_env_xyz"
    }
    response = client.post("/api/v1/ansible/executions", json=payload)
    assert response.status_code == 400
    assert "Unsupported environment" in response.json()["detail"]


def test_api_create_execution_nonexistent_application():
    payload = {
        "playbook_name": "configure_application",
        "application_id": 9999999,
        "environment_id": "development"
    }
    response = client.post("/api/v1/ansible/executions", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_api_get_executions_and_detail():
    # List executions
    response = client.get("/api/v1/ansible/executions")
    assert response.status_code == 200
    exec_list = response.json()
    assert isinstance(exec_list, list)
    assert len(exec_list) > 0

    first_id = exec_list[0]["id"]
    detail_res = client.get(f"/api/v1/ansible/executions/{first_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == first_id
    assert "status" in detail


def test_api_retry_execution():
    list_res = client.get("/api/v1/ansible/executions")
    first_id = list_res.json()[0]["id"]

    retry_res = client.post(f"/api/v1/ansible/executions/{first_id}/retry")
    assert retry_res.status_code == 200
    data = retry_res.json()
    assert data["id"] == first_id
    assert data["status"] == "PENDING"
