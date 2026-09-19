import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.terraform_run import TerraformRun
from app.services.terraform.terraform_client import TerraformClient, strip_ansi
from app.services.terraform.plan_service import TerraformPlanService
from app.services.terraform.apply_service import TerraformApplyService
from app.services.terraform.exceptions import (
    TerraformError,
    TerraformNotInstalledError,
    TerraformSecurityError,
    TerraformPlanError,
    TerraformApplyError,
)

client = TestClient(app)


# =========================================================================
# 1. CLIENT & SECURITY TESTS
# =========================================================================

def test_strip_ansi():
    raw = "\x1b[32mSuccess!\x1b[0m \x1b[1mPlan:\x1b[0m 3 to add"
    assert strip_ansi(raw) == "Success! Plan: 3 to add"
    assert strip_ansi("") == ""


def test_terraform_client_is_installed():
    tf = TerraformClient()
    if not tf.is_installed():
        pytest.skip("Terraform CLI not installed on this test host")
    assert tf.is_installed() is True
    version = tf.get_version()
    assert version is not None
    assert "Terraform" in version


def test_security_forbidden_environment():
    tf = TerraformClient()
    with pytest.raises(TerraformSecurityError) as exc:
        tf.get_working_dir("production; rm -rf /")
    assert "Invalid or forbidden environment" in str(exc.value)

    with pytest.raises(TerraformSecurityError) as exc2:
        tf.get_working_dir("../../../etc")
    assert "Invalid or forbidden environment" in str(exc2.value)


def test_security_path_traversal():
    tf = TerraformClient()
    with pytest.raises(TerraformSecurityError):
        tf.get_working_dir("..")


def test_parse_plan_output():
    tf = TerraformClient()
    sample_plan = """
Terraform will perform the following actions:

  # module.kubernetes_base.kubernetes_namespace_v1.devforge will be created
  + resource "kubernetes_namespace_v1" "devforge" {
      + id = (known after apply)
    }

  # module.kubernetes_base.kubernetes_config_map_v1.environment_config will be created
  + resource "kubernetes_config_map_v1" "environment_config" {
      + id = (known after apply)
    }

Plan: 2 to add, 0 to change, 0 to destroy.
"""
    summary = tf._parse_plan_output(sample_plan)
    assert summary["to_add"] == 2
    assert summary["to_change"] == 0
    assert summary["to_destroy"] == 0
    assert len(summary["resources"]) == 2
    assert summary["resources"][0]["name"] == "devforge"
    assert summary["resources"][0]["action"] == "create"


def test_parse_plan_no_changes():
    tf = TerraformClient()
    sample = "No changes. Your infrastructure matches the configuration."
    summary = tf._parse_plan_output(sample)
    assert summary["to_add"] == 0
    assert summary["to_change"] == 0
    assert summary["to_destroy"] == 0


def test_parse_apply_output():
    tf = TerraformClient()
    sample_apply = """
Apply complete! Resources: 2 added, 1 changed, 0 destroyed.

Outputs:
namespace = "devforge"
"""
    summary = tf._parse_apply_output(sample_apply)
    assert summary["added"] == 2
    assert summary["changed"] == 1
    assert summary["destroyed"] == 0
    assert summary["total_managed"] == 3


# =========================================================================
# 2. SERVICE LAYER TESTS
# =========================================================================

def test_plan_service_success(db):
    mock_client = MagicMock()
    mock_client.plan.return_value = (
        "Plan: 3 to add, 0 to change, 0 to destroy.",
        {"to_add": 3, "to_change": 0, "to_destroy": 0, "resources": [{"name": "devforge", "action": "create", "type": "kubernetes_namespace_v1", "symbol": "+"}]}
    )

    service = TerraformPlanService(client=mock_client)
    res = service.generate_plan(db, environment="development")

    assert res["status"] == "PLAN_READY"
    assert res["summary"]["to_add"] == 3

    # Verify run persisted in database
    run = db.query(TerraformRun).filter(TerraformRun.id == res["run_id"]).first()
    assert run is not None
    assert run.status == "PLAN_READY"
    assert run.operation == "plan"
    assert run.resources_count == 3


def test_plan_service_failure(db):
    mock_client = MagicMock()
    mock_client.plan.side_effect = TerraformPlanError("Syntax error in main.tf line 4")

    service = TerraformPlanService(client=mock_client)
    with pytest.raises(TerraformPlanError):
        service.generate_plan(db, environment="development")

    # Verify FAILED run was recorded
    failed_run = db.query(TerraformRun).order_by(TerraformRun.id.desc()).first()
    assert failed_run is not None
    assert failed_run.status == "FAILED"
    assert "Syntax error in main.tf" in failed_run.error_message


def test_apply_service_success(db):
    mock_client = MagicMock()
    mock_client.apply.return_value = (
        "Apply complete! Resources: 3 added, 0 changed, 0 destroyed.",
        {"added": 3, "changed": 0, "destroyed": 0, "total_managed": 3}
    )

    service = TerraformApplyService(client=mock_client)
    res = service.apply_infrastructure(db, environment="development")

    assert res["status"] == "APPLIED"
    assert res["resources_count"] == 3

    run = db.query(TerraformRun).filter(TerraformRun.id == res["run_id"]).first()
    assert run is not None
    assert run.status == "APPLIED"
    assert run.operation == "apply"


def test_apply_service_idempotency_no_changes(db):
    mock_client = MagicMock()
    mock_client.apply.return_value = (
        "No changes. Your infrastructure matches the configuration.\nApply complete! Resources: 0 added, 0 changed, 0 destroyed.",
        {"added": 0, "changed": 0, "destroyed": 0, "total_managed": 0}
    )

    service = TerraformApplyService(client=mock_client)
    res = service.apply_infrastructure(db, environment="development")

    assert res["status"] == "APPLIED"
    assert res["resources_count"] == 3  # Converges to active managed count


# =========================================================================
# 3. REST API ENDPOINTS
# =========================================================================

def test_api_get_terraform_status():
    resp = client.get("/api/v1/infrastructure/terraform")
    assert resp.status_code == 200
    data = resp.json()
    assert data["installed"] is True
    assert "Terraform" in data["version"]
    assert data["environment"] == "development"
    assert data["provider"] == "Kubernetes (Local)"
    assert "status" in data
    assert "resources_count" in data


@patch("app.api.api_v1.infrastructure.plan_service.client")
def test_api_plan_terraform_success(mock_client):
    mock_client.plan.return_value = (
        "Plan: 3 to add, 0 to change, 0 to destroy.",
        {"to_add": 3, "to_change": 0, "to_destroy": 0, "has_changes": True}
    )
    resp = client.post("/api/v1/infrastructure/terraform/plan", json={"environment": "development"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PLAN_READY"
    assert "run_id" in data
    assert "summary" in data
    assert "plan_output" in data


def test_api_plan_terraform_invalid_environment():
    resp = client.post("/api/v1/infrastructure/terraform/plan", json={"environment": "malicious_env;rm"})
    assert resp.status_code == 400
    assert "Invalid or forbidden environment" in resp.json()["detail"]


@patch("app.api.api_v1.infrastructure.apply_service.client")
def test_api_apply_terraform_success(mock_client):
    mock_client.apply.return_value = (
        "Apply complete! Resources: 3 added, 0 changed, 0 destroyed.",
        {"added": 3, "changed": 0, "destroyed": 0, "total_managed": 3}
    )
    resp = client.post("/api/v1/infrastructure/terraform/apply", json={"environment": "development"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPLIED"
    assert data["resources_count"] >= 2
    assert "apply_output" in data


def test_api_get_terraform_runs():
    resp = client.get("/api/v1/infrastructure/terraform/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert len(runs) > 0
    assert "operation" in runs[0]
    assert "status" in runs[0]


def test_api_get_terraform_run_detail():
    list_resp = client.get("/api/v1/infrastructure/terraform/runs")
    run_id = list_resp.json()[0]["id"]

    resp = client.get(f"/api/v1/infrastructure/terraform/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


def test_api_get_terraform_run_not_found():
    resp = client.get("/api/v1/infrastructure/terraform/runs/999999")
    assert resp.status_code == 404
