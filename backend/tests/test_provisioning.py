import os
import shutil
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db.session import engine, SessionLocal
from app.models.application import Application
from app.models.activity import Activity
from app.services.provisioning.project_generator import project_generator, get_workspace_root

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def clean_test_data():
    db = SessionLocal()
    try:
        test_apps = db.query(Application).filter(Application.name.like("test-%")).all()
        for app_obj in test_apps:
            app_dir = get_workspace_root() / f"app_{app_obj.id}"
            if app_dir.exists():
                shutil.rmtree(app_dir, ignore_errors=True)
            db.delete(app_obj)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def cleanup_workspace():
    clean_test_data()
    yield
    clean_test_data()


# 1. Valid Python Application Creation
def test_create_python_application(client):
    app_name = "test-py-service"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "staging",
        "port": 8000,
        "replicas": 2,
        "database_type": "postgresql",
        "deployment_strategy": "rolling"
    }
    response = client.post("/api/v1/applications?sync=true", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["provisioning_status"] == "READY"
    assert data["application"]["name"] == app_name
    assert data["application"]["template"] == "python-fastapi"
    assert data["application"]["database_type"] == "postgresql"
    assert data["application"]["deployment_strategy"] == "rolling"

    # Verify project on disk in isolated workspace app_{id}
    app_id = data["application"]["id"]
    target_dir = get_workspace_root() / f"app_{app_id}"
    assert target_dir.exists()
    assert (target_dir / "main.py").exists()
    assert (target_dir / "requirements.txt").exists()
    assert (target_dir / "Dockerfile").exists()
    assert (target_dir / "devforge.yaml").exists()
    assert (target_dir / ".github" / "workflows" / "ci.yml").exists()


# 2. Valid React Application Creation
def test_create_react_application(client):
    app_name = "test-react-frontend"
    payload = {
        "name": app_name,
        "runtime": "react",
        "template": "react-vite",
        "environment": "production",
        "port": 3000,
        "replicas": 3,
        "database_type": "none",
        "deployment_strategy": "rolling"
    }
    response = client.post("/api/v1/applications?sync=true", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["provisioning_status"] == "READY"
    assert data["application"]["name"] == app_name
    assert data["application"]["template"] == "react-vite"

    app_id = data["application"]["id"]
    target_dir = get_workspace_root() / f"app_{app_id}"
    assert target_dir.exists()
    assert (target_dir / "package.json").exists()
    assert (target_dir / "index.html").exists()
    assert (target_dir / "vite.config.ts").exists()
    assert (target_dir / "Dockerfile").exists()
    assert (target_dir / "devforge.yaml").exists()
    assert (target_dir / ".github" / "workflows" / "ci.yml").exists()


# 3. Valid Go Application Creation
def test_create_go_application(client):
    app_name = "test-go-service"
    payload = {
        "name": app_name,
        "runtime": "go",
        "template": "go-microservice",
        "environment": "development",
        "port": 8080,
        "replicas": 1,
        "database_type": "redis",
        "deployment_strategy": "recreate"
    }
    response = client.post("/api/v1/applications?sync=true", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["provisioning_status"] == "READY"
    assert data["application"]["template"] == "go-microservice"

    app_id = data["application"]["id"]
    target_dir = get_workspace_root() / f"app_{app_id}"
    assert target_dir.exists()
    assert (target_dir / "main.go").exists()
    assert (target_dir / "go.mod").exists()
    assert (target_dir / "Dockerfile").exists()
    assert (target_dir / "devforge.yaml").exists()
    assert (target_dir / ".github" / "workflows" / "ci.yml").exists()


# 4. Valid Node.js Application Creation
def test_create_node_application(client):
    app_name = "test-node-service"
    payload = {
        "name": app_name,
        "runtime": "node",
        "template": "node-service",
        "environment": "staging",
        "port": 3000,
        "replicas": 2,
        "database_type": "mysql",
        "deployment_strategy": "rolling"
    }
    response = client.post("/api/v1/applications?sync=true", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["provisioning_status"] == "READY"
    assert data["application"]["template"] == "node-service"

    app_id = data["application"]["id"]
    target_dir = get_workspace_root() / f"app_{app_id}"
    assert target_dir.exists()
    assert (target_dir / "server.js").exists()
    assert (target_dir / "package.json").exists()
    assert (target_dir / "Dockerfile").exists()
    assert (target_dir / "devforge.yaml").exists()
    assert (target_dir / ".github" / "workflows" / "ci.yml").exists()


# 5. Invalid Runtime Rejection
def test_invalid_runtime(client):
    payload = {
        "name": "test-invalid-runtime",
        "runtime": "unsupported-runtime-xyz",
        "template": "python-fastapi",
        "environment": "development"
    }
    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 422
    assert "Invalid runtime" in str(response.json())


# 6. Invalid Template Rejection
def test_invalid_template(client):
    payload = {
        "name": "test-invalid-template",
        "runtime": "python",
        "template": "non-existent-template",
        "environment": "development"
    }
    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 422
    assert "Invalid template" in str(response.json())


# 7. Invalid Application Name (Path Traversal & Bad Chars)
def test_invalid_application_name(client):
    bad_names = [
        "../traversal-app",
        "bad_uppercase_NAME",
        "-leading-hyphen",
        "trailing-hyphen-",
        "has spaces in name",
        "has$symbols!"
    ]
    for bad in bad_names:
        payload = {
            "name": bad,
            "runtime": "python",
            "template": "python-fastapi",
            "environment": "development"
        }
        response = client.post("/api/v1/applications", json=payload)
        assert response.status_code == 422


# 8. Duplicate Application Name (409 Conflict)
def test_duplicate_application_name(client):
    app_name = "test-dup-service"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development"
    }
    res1 = client.post("/api/v1/applications", json=payload)
    assert res1.status_code == 201

    # Second attempt with same name must conflict
    res2 = client.post("/api/v1/applications", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


# 9. Generated Project Exists
def test_generated_project_exists(client):
    app_name = "test-gen-exists"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    data = res.json()
    app_id = data["application"]["id"]
    project_path = get_workspace_root() / f"app_{app_id}"
    assert project_path.exists()
    assert project_path.is_dir()


# 10. devforge.yaml Exists in Generated Project
def test_devforge_yaml_exists(client):
    app_name = "test-gen-yaml"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8500
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    data = res.json()
    app_id = data["application"]["id"]
    yaml_file = get_workspace_root() / f"app_{app_id}" / "devforge.yaml"
    assert yaml_file.exists()
    assert yaml_file.is_file()
    assert yaml_file.stat().st_size > 0


# 11. Generated Manifest Contains Correct Application Information
def test_manifest_contents_correct(client):
    app_name = "test-gen-contents"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "staging",
        "port": 8800,
        "database_type": "postgresql",
        "deployment_strategy": "canary",
        "replicas": 4,
        "version": "v1.2.0"
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    data = res.json()
    app_id = data["application"]["id"]
    yaml_file = get_workspace_root() / f"app_{app_id}" / "devforge.yaml"
    content = yaml_file.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    assert parsed["apiVersion"] == "devforge/v1"
    assert parsed["kind"] == "ApplicationManifest"
    assert parsed["metadata"]["name"] == app_name
    assert parsed["metadata"]["version"] == "v1.2.0"
    assert parsed["spec"]["port"] == 8800
    assert parsed["spec"]["database"]["type"] == "postgresql"
    assert parsed["spec"]["deployment"]["strategy"] == "canary"
    assert parsed["spec"]["deployment"]["replicas"] == 4


# 12. Provisioning Failure Handling
def test_provisioning_failure_handling(monkeypatch, client):
    # Simulate non-retryable template directory missing
    def raise_generator_error(*args, **kwargs):
        raise FileNotFoundError("Template directory not found: templates/python-fastapi")

    monkeypatch.setattr(project_generator, "generate_project", raise_generator_error)

    fail_app_name = "test-fail-recovery"
    payload = {
        "name": fail_app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development"
    }
    response = client.post("/api/v1/applications?sync=true", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["provisioning_status"] == "FAILED"

    # Verify that the application was recorded in PostgreSQL as FAILED with error message
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.name == fail_app_name).first()
        assert app_record is not None
        assert app_record.provisioning_status == "FAILED"
        assert app_record.status == "failed"
        assert "Template directory not found" in app_record.provisioning_error

        # Verify activity recorded for the failure
        act = db.query(Activity).filter(
            Activity.target == fail_app_name,
            Activity.action == "Application provisioning failed"
        ).first()
        assert act is not None
        assert act.status == "failed"
    finally:
        db.close()


# 13. Activity Events Recorded
def test_activity_events_recorded(client):
    app_name = "test-activity-events"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development"
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201

    db = SessionLocal()
    try:
        events = db.query(Activity).filter(Activity.target == app_name).all()
        actions = [e.action for e in events]
        assert "Application creation requested" in actions
        assert "Project generation completed" in actions
    finally:
        db.close()


# 14. PostgreSQL Persistence Works for Phase 2 Fields
def test_postgresql_persistence_phase2_fields(client):
    app_name = "test-persist-phase2"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "production",
        "port": 9100,
        "database_type": "postgresql",
        "deployment_strategy": "canary",
        "replicas": 3
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    data = res.json()
    app_id = data["application"]["id"]

    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.name == app_name).first()
        assert app_record is not None
        assert app_record.template == "python-fastapi"
        assert app_record.database_type == "postgresql"
        assert app_record.deployment_strategy == "canary"
        assert app_record.provisioning_status == "READY"
        assert app_record.provisioning_error is None
        assert app_record.generated_path == f".devforge/generated/app_{app_id}"
        assert app_record.manifest_yaml is not None
        assert "apiVersion: devforge/v1" in app_record.manifest_yaml

        # Raw SQL query verification against PostgreSQL
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT template, database_type, deployment_strategy, provisioning_status FROM applications WHERE name = :name"),
                {"name": app_name}
            ).fetchone()
            assert row is not None
            assert row[0] == "python-fastapi"
            assert row[1] == "postgresql"
            assert row[2] == "canary"
            assert row[3] == "READY"
    finally:
        db.close()
