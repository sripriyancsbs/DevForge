import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.services.ci.workflow_generator import workflow_generator, CIWorkflowGenerationError
from app.services.ci.workflow_service import workflow_service
from app.models.application import Application
from app.db.session import SessionLocal





def test_workflow_generator_all_templates():
    """Verify workflow generator produces valid YAML containing required CI stages for each template."""
    templates = [
        ("python-fastapi", "pytest", "Python 3.12"),
        ("react-vite", "npm run build", "Node.js 20"),
        ("node-service", "npm test", "Node.js 20"),
        ("go-microservice", "go test", "Go 1.22"),
    ]

    for tpl_id, expected_cmd, expected_env in templates:
        yml = workflow_generator.generate_workflow_yaml(
            template_id=tpl_id,
            app_name=f"test-{tpl_id}-app",
            port=8080
        )
        assert expected_cmd in yml
        assert expected_env in yml
        assert "docker build" in yml

        # Verify strict YAML syntax
        parsed = yaml.safe_load(yml)
        assert parsed["name"] == "CI"
        assert "jobs" in parsed
        assert "build-and-test" in parsed["jobs"]


def test_workflow_generator_unsupported_template():
    """Verify workflow generator raises CIWorkflowGenerationError on unknown template."""
    with pytest.raises(CIWorkflowGenerationError):
        workflow_generator.generate_workflow_yaml("unknown-ruby-template", "ruby-app")


def test_generate_ci_workflow_in_workspace(tmp_path):
    """Verify workflow_service writes .github/workflows/ci.yml into isolated workspace."""
    wf_file = workflow_service.generate_ci_workflow(
        workspace_path=tmp_path,
        template_id="python-fastapi",
        app_name="ci-test-workspace-app",
        app_port=8000
    )
    assert wf_file.exists()
    assert wf_file.name == "ci.yml"
    assert wf_file.parent.name == "workflows"
    assert wf_file.parent.parent.name == ".github"

    content = wf_file.read_text(encoding="utf-8")
    assert "pytest" in content


def test_normalize_ci_status():
    """Verify normalization of GitHub Actions run status into DevForge standard statuses."""
    assert workflow_service.normalize_ci_status("completed", "success") == "PASSED"
    assert workflow_service.normalize_ci_status("completed", "failure") == "FAILED"
    assert workflow_service.normalize_ci_status("completed", "timed_out") == "FAILED"
    assert workflow_service.normalize_ci_status("completed", "cancelled") == "FAILED"
    assert workflow_service.normalize_ci_status("in_progress", None) == "RUNNING"
    assert workflow_service.normalize_ci_status("queued", None) == "QUEUED"
    assert workflow_service.normalize_ci_status("unknown", None) == "UNKNOWN"
    assert workflow_service.normalize_ci_status(None, None) == "UNKNOWN"


def test_get_application_ci_status_endpoint(client):
    """Verify GET /api/v1/applications/{id}/ci endpoint."""
    import uuid
    app_name = f"ci-endpoint-app-{uuid.uuid4().hex[:6]}"
    # 1. Create app
    res = client.post("/api/v1/applications?sync=true", json={
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000
    })
    assert res.status_code == 201
    app_id = res.json()["application"]["id"]

    # 2. Get CI status
    ci_res = client.get(f"/api/v1/applications/{app_id}/ci")
    assert ci_res.status_code == 200
    data = ci_res.json()
    assert "status" in data
    assert data["application_id"] == app_id
    assert data["application_name"] == app_name
    assert data["workflow"] == "CI"


def test_refresh_application_ci_status_endpoint(client):
    """Verify POST /api/v1/applications/{id}/ci/refresh endpoint with mocked GitHub response."""
    import uuid
    app_name = f"ci-refresh-app-{uuid.uuid4().hex[:6]}"
    # 1. Create app
    res = client.post("/api/v1/applications?sync=true", json={
        "name": app_name,
        "runtime": "react",
        "template": "react-vite",
        "environment": "development",
        "port": 3000
    })
    assert res.status_code == 201
    app_id = res.json()["application"]["id"]

    # 2. Mock github_client.get_workflow_runs
    mock_runs = [{
        "id": 987654321,
        "name": "CI",
        "status": "completed",
        "conclusion": "success",
        "html_url": f"https://github.com/sripriyancsbs/{app_name}/actions/runs/987654321",
        "created_at": "2026-09-18T17:00:00Z",
        "updated_at": "2026-09-18T17:03:00Z"
    }]

    with patch("app.services.ci.workflow_service.github_client.get_workflow_runs", return_value=mock_runs):
        refresh_res = client.post(f"/api/v1/applications/{app_id}/ci/refresh")
        assert refresh_res.status_code == 200
        data = refresh_res.json()
        assert data["status"] == "PASSED"
        assert data["run_id"] == "987654321"
        assert data["run_url"] == f"https://github.com/sripriyancsbs/{app_name}/actions/runs/987654321"


def test_ci_endpoints_not_found(client):
    """Verify 404 for nonexistent applications."""
    assert client.get("/api/v1/applications/999999/ci").status_code == 404
    assert client.post("/api/v1/applications/999999/ci/refresh").status_code == 404
