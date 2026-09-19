import pytest
import yaml
from unittest.mock import MagicMock, patch

from app.services.kubernetes.manifest_generator import (
    ManifestGenerator,
    manifest_generator,
    sanitize_k8s_name,
)
from app.services.kubernetes.exceptions import (
    KubernetesError,
    KubernetesClusterUnavailableError,
    KubernetesAuthError,
    KubernetesNamespaceError,
    KubernetesManifestError,
    KubernetesDeploymentError,
    KubernetesRolloutTimeoutError,
)
from app.services.kubernetes.kubernetes_client import KubernetesClient
from app.services.kubernetes.deployment_service import DeploymentService
from app.models.application import Application
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.activity import Activity


# ============================================================================
# 1. MANIFEST GENERATOR TESTS
# ============================================================================

def test_sanitize_k8s_name():
    assert sanitize_k8s_name("My_Awesome-App.Service") == "my-awesome-app-service"
    assert sanitize_k8s_name("---Test--App---") == "test-app"
    assert sanitize_k8s_name("") == "app"
    assert sanitize_k8s_name("A" * 100) == ("a" * 63)


def test_manifest_generator_all_templates():
    templates_expected = {
        "python-fastapi": {"port": 8000, "probe": "/healthz"},
        "node-service": {"port": 3000, "probe": "/healthz"},
        "go-microservice": {"port": 8080, "probe": "/health"},
        "react-vite": {"port": 3000, "probe": "/"},
    }

    for tpl, expected in templates_expected.items():
        yamls = manifest_generator.generate_manifest_yamls(
            application_name=f"test-{tpl}",
            image=f"ghcr.io/sripriyancsbs/test-{tpl}:sha-1234567",
            template=tpl,
            namespace="devforge",
        )

        assert "deployment" in yamls
        assert "service" in yamls
        assert "configmap" in yamls
        assert yamls["port"] == expected["port"]

        # Parse generated YAMLs to ensure strictly valid Kubernetes syntax
        dep_data = yaml.safe_load(yamls["deployment"])
        assert dep_data["apiVersion"] == "apps/v1"
        assert dep_data["kind"] == "Deployment"
        assert dep_data["metadata"]["namespace"] == "devforge"
        assert dep_data["spec"]["template"]["spec"]["containers"][0]["image"] == f"ghcr.io/sripriyancsbs/test-{tpl}:sha-1234567"
        assert dep_data["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"] == expected["port"]
        assert dep_data["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["httpGet"]["path"] == expected["probe"]

        svc_data = yaml.safe_load(yamls["service"])
        assert svc_data["apiVersion"] == "v1"
        assert svc_data["kind"] == "Service"
        assert svc_data["spec"]["ports"][0]["port"] == expected["port"]

        cm_data = yaml.safe_load(yamls["configmap"])
        assert cm_data["apiVersion"] == "v1"
        assert cm_data["kind"] == "ConfigMap"


def test_manifest_generator_custom_port_override():
    yamls = manifest_generator.generate_manifest_yamls(
        application_name="custom-port-app",
        image="ghcr.io/sripriyancsbs/custom-port-app:v1",
        port=9090,
        template="python-fastapi",
    )
    assert yamls["port"] == 9090
    dep_data = yaml.safe_load(yamls["deployment"])
    assert dep_data["spec"]["template"]["spec"]["containers"][0]["ports"][0]["containerPort"] == 9090


def test_manifest_generator_empty_inputs_fail():
    with pytest.raises(KubernetesManifestError):
        manifest_generator.generate_manifest_yamls(application_name="", image="ghcr.io/test:v1")
    with pytest.raises(KubernetesManifestError):
        manifest_generator.generate_manifest_yamls(application_name="test", image="")


def test_manifest_generator_replicas_and_secrets():
    yamls = manifest_generator.generate_manifest_yamls(
        application_name="secure-app",
        image="ghcr.io/sripriyancsbs/secure-app:sha-abc",
        replicas=3,
        image_pull_secret="devforge-ghcr-secret",
    )
    dep_data = yaml.safe_load(yamls["deployment"])
    assert dep_data["spec"]["replicas"] == 3
    assert dep_data["spec"]["template"]["spec"]["imagePullSecrets"][0]["name"] == "devforge-ghcr-secret"


# ============================================================================
# 2. KUBERNETES CLIENT UNIT TESTS (MOCKED)
# ============================================================================

def test_kubernetes_client_forbidden_system_namespace():
    kc = KubernetesClient()
    with pytest.raises(KubernetesNamespaceError) as exc_info:
        kc.ensure_namespace("kube-system")
    assert "system namespace" in str(exc_info.value)


@patch.object(KubernetesClient, "_ensure_client")
def test_kubernetes_client_cluster_status_mocked(mock_ensure):
    kc = KubernetesClient()
    mock_v1 = MagicMock()
    mock_node = MagicMock()
    mock_node.metadata.name = "node-1"
    mock_cond = MagicMock()
    mock_cond.type = "Ready"
    mock_cond.status = "True"
    mock_node.status.conditions = [mock_cond]
    mock_node.status.node_info.kubelet_version = "v1.31.0"
    mock_node.status.node_info.os_image = "Linux"
    mock_v1.list_node.return_value.items = [mock_node]
    kc._core_v1 = mock_v1

    with patch("kubernetes.client.VersionApi") as mock_v_api:
        mock_v_instance = MagicMock()
        mock_v_instance.get_code.return_value.git_version = "v1.31.0"
        mock_v_api.return_value = mock_v_instance

        status = kc.get_cluster_status()
        assert status["connected"] is True
        assert status["node_count"] == 1
        assert status["nodes"][0]["name"] == "node-1"
        assert status["nodes"][0]["ready"] is True


@patch.object(KubernetesClient, "_ensure_client")
def test_kubernetes_client_verify_rollout_detects_image_pull_error(mock_ensure):
    kc = KubernetesClient()
    mock_apps = MagicMock()
    dep_mock = MagicMock()
    dep_mock.status.ready_replicas = 0
    dep_mock.status.updated_replicas = 0
    mock_apps.read_namespaced_deployment.return_value = dep_mock
    kc._apps_v1 = mock_apps

    # Mock pods returning ErrImagePull
    with patch.object(kc, "get_pods_for_application") as mock_get_pods:
        mock_get_pods.return_value = [
            {"name": "pod-1", "phase": "Pending", "ready": False, "message": "ErrImagePull: image not found"}
        ]
        is_ready, ready_reps, pods, err = kc.verify_rollout(
            deployment_name="test-dep",
            application_name="test-app",
            expected_replicas=1,
            timeout=2,
            poll_interval=0.1,
        )
        assert is_ready is False
        assert ready_reps == 0
        assert "image pull failure" in err.lower()


# ============================================================================
# 3. DEPLOYMENT SERVICE & API INTEGRATION TESTS
# ============================================================================

def test_kubernetes_cluster_status_api(client):
    res = client.get("/api/v1/integrations/kubernetes/status")
    assert res.status_code == 200
    data = res.json()
    assert "connected" in data
    assert "provider" in data
    assert "namespace" in data


def test_deploy_nonexistent_application(client):
    res = client.post("/api/v1/applications/999999/deploy", json={})
    assert res.status_code == 404


def test_get_deployment_not_found(client):
    res = client.get("/api/v1/applications/999999/deployment")
    assert res.status_code == 404


def test_redeploy_nonexistent_application(client):
    res = client.post("/api/v1/applications/999999/deployment/redeploy", json={})
    assert res.status_code == 404


def test_stop_nonexistent_application(client):
    res = client.post("/api/v1/applications/999999/deployment/stop")
    assert res.status_code == 404


def test_deployment_lifecycle_end_to_end(client, db):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    app_name = f"k8s-svc-{suffix}"

    # 1. Create a test application
    app_data = {
        "name": app_name,
        "team": "Platform Engineering",
        "runtime": "Python 3.12 (FastAPI)",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000,
        "replicas": 1,
        "repository_owner": "sripriyancsbs",
        "repository_name": app_name,
        "repository_url": f"https://github.com/sripriyancsbs/{app_name}",
    }
    create_res = client.post("/api/v1/applications", json=app_data)
    assert create_res.status_code in (200, 201)
    res_data = create_res.json()
    app_id = res_data["application"]["id"]

    # 2. Deploy using deployment service with mocked k8s client apply & rollout
    with patch("app.services.kubernetes.deployment_service.kubernetes_client") as mock_kc:
        mock_kc.ensure_namespace.return_value = "devforge"
        mock_kc.ensure_image_pull_secret.return_value = "devforge-ghcr-secret"
        mock_kc.apply_configmap.return_value = f"devforge-{app_name}-config"
        mock_kc.apply_service.return_value = (f"devforge-{app_name}-svc", 31234)
        mock_kc.apply_deployment.return_value = f"devforge-{app_name}"
        mock_kc.get_pods_for_application.return_value = [
            {"name": f"devforge-{app_name}-abc12", "phase": "Running", "ready": True, "restart_count": 0}
        ]
        mock_kc.verify_rollout.return_value = (
            True,
            1,
            [{"name": f"devforge-{app_name}-abc12", "phase": "Running", "ready": True, "restart_count": 0}],
            None
        )

        deploy_res = client.post(
            f"/api/v1/applications/{app_id}/deploy",
            json={"image_tag": "sha-test1234", "replicas": 1}
        )
        assert deploy_res.status_code == 200
        deploy_body = deploy_res.json()
        assert deploy_body["status"] == "RUNNING"
        assert deploy_body["ready_replicas"] == 1
        assert deploy_body["replicas"] == 1
        assert deploy_body["image_tag"] == "sha-test1234"
        assert deploy_body["node_port"] == 31234
        assert len(deploy_body["pods"]) == 1
        assert deploy_body["pods"][0]["ready"] is True

        # 3. GET /applications/{id}/deployment
        get_res = client.get(f"/api/v1/applications/{app_id}/deployment")
        assert get_res.status_code == 200
        get_body = get_res.json()
        assert get_body["status"] == "RUNNING"
        assert get_body["service_name"] == f"devforge-{app_name}-svc"

        # 4. POST /applications/{id}/deployment/redeploy
        mock_kc.verify_rollout.return_value = (
            True,
            1,
            [{"name": f"devforge-{app_name}-def56", "phase": "Running", "ready": True, "restart_count": 0}],
            None
        )
        redeploy_res = client.post(
            f"/api/v1/applications/{app_id}/deployment/redeploy",
            json={"image_tag": "sha-test5678"}
        )
        assert redeploy_res.status_code == 200
        assert redeploy_res.json()["image_tag"] == "sha-test5678"

        # 5. POST /applications/{id}/deployment/stop
        mock_kc.stop_deployment.return_value = True
        stop_res = client.post(f"/api/v1/applications/{app_id}/deployment/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "STOPPED"

        # 6. Verify activity events were recorded
        activities = db.query(Activity).filter(Activity.target == app_name).all()
        actions = [a.action for a in activities]
        assert "Deployment requested" in actions
        assert "Manifest generated" in actions
        assert "Kubernetes deployment started" in actions
        assert "Deployment ready" in actions
        assert "Deployment redeployed" in actions
        assert "Deployment stopped" in actions
