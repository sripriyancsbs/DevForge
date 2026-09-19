import pytest
import os
import yaml
from unittest.mock import MagicMock, patch
from kubernetes.client.rest import ApiException

from app.services.argocd.manifest_service import GitOpsManifestService, gitops_manifest_service
from app.services.argocd.argocd_client import ArgoCDClient
from app.services.argocd.application_service import GitOpsApplicationService
from app.services.argocd.sync_service import GitOpsSyncService
from app.services.argocd.exceptions import (
    ArgoCDError,
    ArgoCDUnavailableError,
    ArgoCDApplicationNotFoundError,
    ArgoCDSyncError,
)
from app.models.application import Application
from app.models.gitops_application import GitOpsApplication
from app.models.gitops_operation import GitOpsOperation
from app.models.activity import Activity


# ==============================================================================
# 1. KUSTOMIZE MANIFEST GENERATION TESTS
# ==============================================================================

def test_manifest_generation_structure():
    """Verify generated base and overlay manifests conform to Kustomize conventions."""
    app = Application(
        name="payment-api",
        slug="payment-api",
        template="python-fastapi",
        port=8000,
        replicas=3,
        image_repository="ghcr.io/sripriyancsbs/payment-api",
    )

    manifests = gitops_manifest_service.generate_manifests(
        application=app,
        environment="development",
        image_tag="sha-4f81c9a",
        replicas=2,
    )

    assert "base/deployment.yaml" in manifests
    assert "base/service.yaml" in manifests
    assert "base/kustomization.yaml" in manifests
    assert "overlays/development/kustomization.yaml" in manifests
    assert "overlays/development/patch.yaml" in manifests

    # Check base manifests
    base_kustomize = yaml.safe_load(manifests["base/kustomization.yaml"])
    assert base_kustomize["apiVersion"] == "kustomize.config.k8s.io/v1beta1"
    assert "deployment.yaml" in base_kustomize["resources"]
    assert "service.yaml" in base_kustomize["resources"]

    base_deploy = yaml.safe_load(manifests["base/deployment.yaml"])
    assert base_deploy["metadata"]["name"] == "devforge-payment-api"
    container = base_deploy["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "ghcr.io/sripriyancsbs/payment-api:sha-4f81c9a"
    assert container["ports"][0]["containerPort"] == 8000

    base_svc = yaml.safe_load(manifests["base/service.yaml"])
    assert base_svc["metadata"]["name"] == "devforge-payment-api-svc"
    assert base_svc["spec"]["ports"][0]["port"] == 8000
    assert base_svc["spec"]["ports"][0]["targetPort"] == 8000

    # Check overlay manifests
    overlay_kustomize = yaml.safe_load(manifests["overlays/development/kustomization.yaml"])
    assert "../../base" in overlay_kustomize["resources"]
    assert any(p.get("path") == "patch.yaml" for p in overlay_kustomize.get("patches", []))

    overlay_patch = yaml.safe_load(manifests["overlays/development/patch.yaml"])
    assert overlay_patch["spec"]["replicas"] == 2


def test_manifest_write_and_path_resolution(tmp_path):
    """Test writing manifests to disk workspace."""
    service = GitOpsManifestService(gitops_root=str(tmp_path))
    app = Application(
        name="catalog-service",
        slug="catalog-service",
        template="node-service",
        port=3000,
        replicas=1,
        image_repository="ghcr.io/sripriyancsbs/catalog-service",
    )

    overlay_dir = service.write_manifests_to_disk(
        application=app,
        environment="development",
        image_tag="v1.2.0",
        replicas=2,
    )

    assert os.path.exists(overlay_dir)
    target_dir = service.get_application_gitops_dir(app.slug)
    assert os.path.exists(target_dir / "base" / "deployment.yaml")
    assert os.path.exists(target_dir / "overlays" / "development" / "kustomization.yaml")


# ==============================================================================
# 2. ARGO CD CLIENT UNIT TESTS (MOCKED K8S API)
# ==============================================================================

@patch("app.services.argocd.argocd_client.client.CustomObjectsApi")
def test_argocd_client_is_available_true(mock_api_cls):
    mock_api = MagicMock()
    mock_api.list_namespaced_custom_object.return_value = {"items": []}
    mock_api_cls.return_value = mock_api

    client = ArgoCDClient()
    client._k8s_ready = True
    client._k8s_api = mock_api

    assert client.is_available() is True


@patch("app.services.argocd.argocd_client.client.CustomObjectsApi")
def test_argocd_client_is_available_false(mock_api_cls):
    mock_api = MagicMock()
    mock_api.list_namespaced_custom_object.side_effect = Exception("CRD not found")
    mock_api_cls.return_value = mock_api

    client = ArgoCDClient()
    client._k8s_ready = True
    client._k8s_api = mock_api

    assert client.is_available() is False


@patch("app.services.argocd.argocd_client.client.CustomObjectsApi")
def test_create_or_update_application_create(mock_api_cls):
    mock_api = MagicMock()
    # Simulate not found on get, then successfully creates
    mock_api.get_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")
    mock_api.create_namespaced_custom_object.return_value = {
        "metadata": {"name": "devforge-inventory", "creationTimestamp": "2026-09-19T00:00:00Z"},
        "spec": {
            "source": {"repoURL": "https://github.com/org/repo.git", "path": "apps/inv", "targetRevision": "main"},
            "destination": {"namespace": "devforge"},
            "syncPolicy": {},
        },
        "status": {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}},
    }

    client = ArgoCDClient()
    client._k8s_ready = True
    client._k8s_api = mock_api

    res = client.create_or_update_application(
        name="devforge-inventory",
        repo_url="https://github.com/org/repo.git",
        path="apps/inv",
    )

    assert res["name"] == "devforge-inventory"
    assert res["sync_status"] == "SYNCED"
    assert res["health_status"] == "HEALTHY"
    mock_api.create_namespaced_custom_object.assert_called_once()


@patch("app.services.argocd.argocd_client.client.CustomObjectsApi")
def test_create_or_update_application_update_idempotent(mock_api_cls):
    """Idempotency test: when app already exists, updates spec without recreation."""
    mock_api = MagicMock()
    mock_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "devforge-inventory"},
        "spec": {},
    }
    mock_api.replace_namespaced_custom_object.return_value = {
        "metadata": {"name": "devforge-inventory"},
        "spec": {
            "source": {"repoURL": "https://github.com/org/repo.git", "path": "apps/inv", "targetRevision": "main"},
            "destination": {"namespace": "devforge"},
        },
        "status": {"sync": {"status": "OutOfSync"}, "health": {"status": "Progressing"}},
    }

    client = ArgoCDClient()
    client._k8s_ready = True
    client._k8s_api = mock_api

    res = client.create_or_update_application(
        name="devforge-inventory",
        repo_url="https://github.com/org/repo.git",
        path="apps/inv",
    )

    assert res["sync_status"] == "OUT_OF_SYNC"
    assert res["health_status"] == "PROGRESSING"
    mock_api.replace_namespaced_custom_object.assert_called_once()
    mock_api.create_namespaced_custom_object.assert_not_called()


@patch("app.services.argocd.argocd_client.client.CustomObjectsApi")
def test_drift_detection_parsing(mock_api_cls):
    """Verify drift detection extracts out-of-sync resources."""
    mock_api = MagicMock()
    mock_api.get_namespaced_custom_object.return_value = {
        "metadata": {"name": "devforge-app"},
        "spec": {
            "source": {"repoURL": "repo", "path": "path", "targetRevision": "main"},
            "destination": {"namespace": "devforge"},
        },
        "status": {
            "sync": {"status": "OutOfSync"},
            "health": {"status": "Degraded"},
            "resources": [
                {
                    "group": "apps",
                    "kind": "Deployment",
                    "name": "devforge-app",
                    "namespace": "devforge",
                    "status": "OutOfSync",
                },
                {
                    "group": "",
                    "kind": "Service",
                    "name": "devforge-app-svc",
                    "namespace": "devforge",
                    "status": "Synced",
                }
            ]
        }
    }

    client = ArgoCDClient()
    client._k8s_ready = True
    client._k8s_api = mock_api

    app = client.get_application("devforge-app")
    assert app["sync_status"] == "OUT_OF_SYNC"
    assert app["health_status"] == "DEGRADED"
    assert app["drift_count"] == 1
    assert app["drifted_resources"][0]["kind"] == "Deployment"
    assert app["drifted_resources"][0]["name"] == "devforge-app"


import uuid

# ==============================================================================
# 3. HIGH-LEVEL APPLICATION SERVICE TESTS
# ==============================================================================

def test_enable_gitops_service_workflow(db):
    uid = uuid.uuid4().hex[:6]
    app = Application(
        name=f"order-svc-{uid}",
        slug=f"order-svc-{uid}",
        description="Processes orders",
        repository_url=f"https://github.com/devforge-org/order-{uid}",
        port=8080,
        replicas=2,
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.create_or_update_application.return_value = {
        "name": f"devforge-order-svc-{uid}",
        "sync_status": "SYNCED",
        "health_status": "HEALTHY",
    }
    mock_client.get_application.return_value = {
        "name": f"devforge-order-svc-{uid}",
        "sync_status": "SYNCED",
        "health_status": "HEALTHY",
        "drift_count": 0,
        "drifted_resources": [],
    }

    service = GitOpsApplicationService(client=mock_client)
    gitops_app = service.enable_gitops(
        application_id=app.id,
        db=db,
        auto_sync=True,
        self_heal=True,
    )

    assert gitops_app.argocd_application_name == f"devforge-order-svc-{uid}"
    assert gitops_app.auto_sync_enabled is True
    assert gitops_app.self_heal_enabled is True

    # Check activity record was logged
    activity = db.query(Activity).filter(Activity.target == app.name).first()
    assert activity is not None
    assert activity.action == "gitops_enabled"

    # Idempotent re-run
    gitops_app2 = service.enable_gitops(
        application_id=app.id,
        db=db,
        auto_sync=False,
    )
    assert gitops_app2.id == gitops_app.id
    assert gitops_app2.auto_sync_enabled is False


# ==============================================================================
# 4. ASYNC SYNC SERVICE & QUEUEING TESTS
# ==============================================================================

def test_queue_and_execute_sync(db):
    uid = uuid.uuid4().hex[:6]
    app = Application(
        name=f"billing-svc-{uid}",
        slug=f"billing-svc-{uid}",
        repository_url=f"https://github.com/devforge-org/billing-{uid}",
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    gitops_app = GitOpsApplication(
        application_id=app.id,
        argocd_application_name=f"devforge-billing-svc-{uid}",
        git_repository=f"https://github.com/devforge-org/billing-{uid}",
        git_path=f"applications/billing-svc-{uid}/overlays/development",
        target_revision="main",
        sync_status="OUT_OF_SYNC",
        health_status="HEALTHY",
    )
    db.add(gitops_app)
    db.commit()
    db.refresh(gitops_app)

    mock_client = MagicMock()
    mock_client.is_available.return_value = True
    mock_client.sync_application.return_value = {"sync_status": "SYNCING"}
    mock_client.get_application.return_value = {
        "sync_status": "SYNCED",
        "health_status": "HEALTHY",
        "sync_revision": "c0ffee1",
    }

    sync_service = GitOpsSyncService(client=mock_client)

    # Queue operation
    op = sync_service.queue_operation(
        gitops_application_id=gitops_app.id,
        operation_type="SYNC",
        db=db,
    )
    assert op.status == "PENDING"
    assert op.operation_type == "SYNC"

    # Execute operation (simulating worker process)
    completed_op = sync_service.execute_operation(op.id, db)
    assert completed_op.status == "SUCCESS"
    assert completed_op.completed_at is not None

    # Verify gitops_app status updated
    db.refresh(gitops_app)
    assert gitops_app.sync_status == "SYNCED"
    assert gitops_app.last_sync_revision == "c0ffee1"
