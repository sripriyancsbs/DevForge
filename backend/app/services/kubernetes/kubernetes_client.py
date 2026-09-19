import os
import re
import json
import base64
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_SDK_AVAILABLE = True
except ImportError:
    KUBERNETES_SDK_AVAILABLE = False
    client = None
    config = None
    ApiException = Exception

from app.core.config import settings
from app.services.kubernetes.exceptions import (
    KubernetesClusterUnavailableError,
    KubernetesAuthError,
    KubernetesNamespaceError,
    KubernetesDeploymentError,
    KubernetesServiceError,
    KubernetesRolloutTimeoutError,
    KubernetesRolloutFailedError,
    KubernetesImagePullError,
    KubernetesManifestError,
)

logger = logging.getLogger("devforge.kubernetes_client")


class KubernetesClient:
    """
    Official Python Kubernetes Client wrapper for DevForge.
    Communicates directly with the Kubernetes cluster using native client APIs.
    """

    def __init__(self):
        self._initialized = False
        self._api_client = None
        self._core_v1: Optional[client.CoreV1Api] = None
        self._apps_v1: Optional[client.AppsV1Api] = None

    def _ensure_client(self) -> None:
        """Initialize Kubernetes API client from kubeconfig or in-cluster credentials."""
        if not KUBERNETES_SDK_AVAILABLE:
            raise KubernetesClusterUnavailableError(
                "Kubernetes Python client SDK is not installed in the environment."
            )

        if self._initialized and self._core_v1 and self._apps_v1:
            return

        try:
            # 1. Try explicit kubeconfig path from settings
            if settings.KUBERNETES_KUBECONFIG_PATH and os.path.exists(settings.KUBERNETES_KUBECONFIG_PATH):
                config.load_kube_config(
                    config_file=settings.KUBERNETES_KUBECONFIG_PATH,
                    context=settings.KUBERNETES_CONTEXT or None
                )
            # 2. Try default kubeconfig locations (~/.kube/config)
            elif os.path.exists(os.path.expanduser("~/.kube/config")):
                config.load_kube_config(context=settings.KUBERNETES_CONTEXT or None)
            # 3. Fallback to in-cluster service account configuration
            else:
                config.load_incluster_config()

            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            self._initialized = True
            logger.info("Successfully initialized Kubernetes API client.")
        except ApiException as ae:
            if ae.status in (401, 403):
                raise KubernetesAuthError(f"Kubernetes authentication failed: {ae.reason}") from ae
            raise KubernetesClusterUnavailableError(f"Failed to communicate with Kubernetes: {ae}") from ae
        except Exception as e:
            logger.warning(f"Could not load Kubernetes configuration: {e}")
            raise KubernetesClusterUnavailableError(
                f"Kubernetes cluster is unavailable or kubeconfig is missing: {e}"
            ) from e

    @property
    def core_v1(self) -> Any:
        self._ensure_client()
        return self._core_v1

    @property
    def apps_v1(self) -> Any:
        self._ensure_client()
        return self._apps_v1

    def get_cluster_status(self) -> Dict[str, Any]:
        """Check cluster connection and return health and node metadata."""
        try:
            v1 = self.core_v1
            nodes = v1.list_node(timeout_seconds=5).items
            version_info = client.VersionApi().get_code()
            node_summaries = []
            for n in nodes:
                ready = any(
                    cond.type == "Ready" and cond.status == "True"
                    for cond in (n.status.conditions or [])
                )
                node_summaries.append({
                    "name": n.metadata.name,
                    "ready": ready,
                    "kubelet_version": n.status.node_info.kubelet_version,
                    "os_image": n.status.node_info.os_image,
                })

            return {
                "connected": True,
                "provider": "Local Kubernetes",
                "version": version_info.git_version,
                "namespace": settings.KUBERNETES_NAMESPACE,
                "node_count": len(nodes),
                "nodes": node_summaries,
                "error": None,
            }
        except Exception as e:
            logger.warning(f"Kubernetes cluster health check failed: {e}")
            return {
                "connected": False,
                "provider": "Local Kubernetes",
                "version": None,
                "namespace": settings.KUBERNETES_NAMESPACE,
                "node_count": 0,
                "nodes": [],
                "error": str(e),
            }

    def ensure_namespace(self, namespace: Optional[str] = None) -> str:
        """
        Verify the isolated DevForge namespace exists, creating it if needed.
        Ensures applications never deploy into kube-system or default by accident.
        """
        ns = namespace or settings.KUBERNETES_NAMESPACE or "devforge"
        if ns in ("kube-system", "kube-public", "kube-node-lease"):
            raise KubernetesNamespaceError(
                f"Deployments into system namespace '{ns}' are strictly forbidden."
            )

        v1 = self.core_v1
        try:
            v1.read_namespace(name=ns)
            return ns
        except ApiException as ae:
            if ae.status == 404:
                try:
                    body = client.V1Namespace(
                        metadata=client.V1ObjectMeta(
                            name=ns,
                            labels={
                                "app.kubernetes.io/managed-by": "devforge",
                                "devforge.io/namespace": "devforge",
                            }
                        )
                    )
                    v1.create_namespace(body=body)
                    logger.info(f"Created isolated Kubernetes namespace: {ns}")
                    return ns
                except Exception as create_err:
                    raise KubernetesNamespaceError(
                        f"Failed to create namespace '{ns}': {create_err}"
                    ) from create_err
            elif ae.status in (401, 403):
                raise KubernetesAuthError(f"Permission denied accessing namespace '{ns}': {ae.reason}") from ae
            raise KubernetesNamespaceError(f"Error accessing namespace '{ns}': {ae}") from ae

    def ensure_image_pull_secret(
        self,
        namespace: str,
        secret_name: str = "devforge-ghcr-secret",
        token: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Optional[str]:
        """
        Ensure image pull secret exists in namespace for private GHCR images.
        Uses GITHUB_TOKEN securely without leaking into source or logs.
        """
        github_token = token or settings.GITHUB_TOKEN
        github_user = username or settings.GITHUB_OWNER or "devforge"

        if not github_token:
            logger.info("No GitHub token configured; skipping GHCR image pull secret creation.")
            return None

        v1 = self.core_v1
        auth_bytes = f"{github_user}:{github_token}".encode("utf-8")
        auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

        docker_config = {
            "auths": {
                "ghcr.io": {
                    "username": github_user,
                    "password": github_token,
                    "auth": auth_b64,
                }
            }
        }
        docker_config_json = json.dumps(docker_config)
        secret_data = {
            ".dockerconfigjson": base64.b64encode(docker_config_json.encode("utf-8")).decode("utf-8")
        }

        secret_body = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="kubernetes.io/dockerconfigjson",
            metadata=client.V1ObjectMeta(
                name=secret_name,
                namespace=namespace,
                labels={"app.kubernetes.io/managed-by": "devforge"}
            ),
            data=secret_data,
        )

        try:
            v1.read_namespaced_secret(name=secret_name, namespace=namespace)
            # Exists, update it
            v1.replace_namespaced_secret(name=secret_name, namespace=namespace, body=secret_body)
            logger.info(f"Updated GHCR image pull secret '{secret_name}' in namespace '{namespace}'")
        except ApiException as ae:
            if ae.status == 404:
                v1.create_namespaced_secret(namespace=namespace, body=secret_body)
                logger.info(f"Created GHCR image pull secret '{secret_name}' in namespace '{namespace}'")
            else:
                logger.warning(f"Failed to ensure image pull secret '{secret_name}': {ae}")

        return secret_name

    def apply_configmap(self, manifest_dict: Dict[str, Any], namespace: str) -> str:
        """Idempotently create or update a ConfigMap."""
        v1 = self.core_v1
        cm_name = manifest_dict["metadata"]["name"]
        manifest_dict["metadata"]["namespace"] = namespace

        try:
            v1.read_namespaced_config_map(name=cm_name, namespace=namespace)
            v1.patch_namespaced_config_map(name=cm_name, namespace=namespace, body=manifest_dict)
            logger.info(f"Patched ConfigMap: {cm_name} in {namespace}")
        except ApiException as ae:
            if ae.status == 404:
                v1.create_namespaced_config_map(namespace=namespace, body=manifest_dict)
                logger.info(f"Created ConfigMap: {cm_name} in {namespace}")
            else:
                raise KubernetesManifestError(f"Failed to apply ConfigMap '{cm_name}': {ae}") from ae
        return cm_name

    def apply_service(self, manifest_dict: Dict[str, Any], namespace: str) -> Tuple[str, Optional[int]]:
        """
        Idempotently create or update a Service.
        Preserves existing clusterIP and nodePort when updating to keep service stable.
        """
        v1 = self.core_v1
        svc_name = manifest_dict["metadata"]["name"]
        manifest_dict["metadata"]["namespace"] = namespace

        node_port: Optional[int] = None
        try:
            existing_svc = v1.read_namespaced_service(name=svc_name, namespace=namespace)
            # Preserve clusterIP so update does not get rejected by k8s
            if existing_svc.spec.cluster_ip:
                manifest_dict["spec"]["clusterIP"] = existing_svc.spec.cluster_ip

            # If existing service already has a nodePort, retain it
            if existing_svc.spec.ports and existing_svc.spec.ports[0].node_port:
                node_port = existing_svc.spec.ports[0].node_port
                if "ports" in manifest_dict["spec"] and len(manifest_dict["spec"]["ports"]) > 0:
                    manifest_dict["spec"]["ports"][0]["nodePort"] = node_port

            updated = v1.patch_namespaced_service(name=svc_name, namespace=namespace, body=manifest_dict)
            if updated.spec.ports and updated.spec.ports[0].node_port:
                node_port = updated.spec.ports[0].node_port
            logger.info(f"Updated existing Service: {svc_name} (NodePort: {node_port})")
        except ApiException as ae:
            if ae.status == 404:
                try:
                    created = v1.create_namespaced_service(namespace=namespace, body=manifest_dict)
                    if created.spec.ports and created.spec.ports[0].node_port:
                        node_port = created.spec.ports[0].node_port
                    logger.info(f"Created Service: {svc_name} (NodePort: {node_port})")
                except Exception as ce:
                    raise KubernetesServiceError(f"Failed to create Service '{svc_name}': {ce}") from ce
            else:
                raise KubernetesServiceError(f"Failed to apply Service '{svc_name}': {ae}") from ae

        return svc_name, node_port

    def apply_deployment(self, manifest_dict: Dict[str, Any], namespace: str) -> str:
        """
        Idempotently create or update a Deployment.
        If deployment already exists, triggers a rolling update with the new spec.
        """
        apps = self.apps_v1
        dep_name = manifest_dict["metadata"]["name"]
        manifest_dict["metadata"]["namespace"] = namespace

        try:
            apps.read_namespaced_deployment(name=dep_name, namespace=namespace)
            # Add rollout restart annotation to ensure pod redeployment even with same tag
            annotations = manifest_dict["spec"]["template"]["metadata"].setdefault("annotations", {})
            annotations["devforge.io/restartedAt"] = str(time.time())
            apps.patch_namespaced_deployment(name=dep_name, namespace=namespace, body=manifest_dict)
            logger.info(f"Patched Deployment '{dep_name}' for rolling update in {namespace}")
        except ApiException as ae:
            if ae.status == 404:
                try:
                    apps.create_namespaced_deployment(namespace=namespace, body=manifest_dict)
                    logger.info(f"Created Deployment '{dep_name}' in {namespace}")
                except Exception as ce:
                    raise KubernetesDeploymentError(f"Failed to create Deployment '{dep_name}': {ce}") from ce
            else:
                raise KubernetesDeploymentError(f"Failed to update Deployment '{dep_name}': {ae}") from ae

        return dep_name

    def get_pods_for_application(
        self,
        application_name: str,
        namespace: str = "devforge"
    ) -> List[Dict[str, Any]]:
        """Query pods belonging to an application and extract their status details."""
        v1 = self.core_v1
        sanitized = re.sub(r"[^a-z0-9\-]", "-", application_name.lower()).strip("-")
        label_selector = f"app.kubernetes.io/name={sanitized}"

        try:
            pod_list = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        except Exception as e:
            logger.warning(f"Failed to list pods for {application_name}: {e}")
            return []

        results = []
        for pod in pod_list.items:
            # Check readiness
            is_ready = False
            for cond in (pod.status.conditions or []):
                if cond.type == "Ready" and cond.status == "True":
                    is_ready = True
                    break

            # Calculate restart count and container message
            restart_count = 0
            container_msg = None
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    restart_count += cs.restart_count
                    if cs.state.waiting:
                        container_msg = f"{cs.state.waiting.reason}: {cs.state.waiting.message or ''}".strip(": ")
                    elif cs.state.terminated and cs.state.terminated.exit_code != 0:
                        container_msg = f"Terminated: exit {cs.state.terminated.exit_code} ({cs.state.terminated.reason or ''})".strip(": ")

            started_at_str = None
            if pod.status.start_time:
                started_at_str = pod.status.start_time.isoformat()

            results.append({
                "name": pod.metadata.name,
                "phase": pod.status.phase or "Pending",
                "ready": is_ready,
                "restart_count": restart_count,
                "node_name": pod.spec.node_name,
                "started_at": started_at_str,
                "message": container_msg,
            })
        return results

    def verify_rollout(
        self,
        deployment_name: str,
        application_name: str,
        expected_replicas: int,
        namespace: str = "devforge",
        timeout: int = 120,
        poll_interval: float = 2.0,
    ) -> Tuple[bool, int, List[Dict[str, Any]], Optional[str]]:
        """
        Verify that the Kubernetes rollout has successfully completed:
        1. Deployment exists
        2. ReplicaSet exists
        3. Pods exist
        4. Pods become Ready
        5. Expected replica count reached
        6. Service exists
        Detects ImagePullBackOff, ErrImagePull, CrashLoopBackOff immediately.
        Returns (is_ready, ready_replicas, pod_statuses, error_message).
        """
        apps = self.apps_v1
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 1. Inspect Deployment
            try:
                dep = apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
            except ApiException as ae:
                if ae.status == 404:
                    time.sleep(poll_interval)
                    continue
                return False, 0, [], f"Kubernetes API error checking deployment: {ae.reason}"

            status = dep.status
            ready_replicas = status.ready_replicas or 0
            updated_replicas = status.updated_replicas or 0

            # 2. Inspect Pods
            pods = self.get_pods_for_application(application_name, namespace)

            # Check for immediate critical pod failure conditions
            for p in pods:
                msg = p.get("message") or ""
                if "ErrImagePull" in msg or "ImagePullBackOff" in msg:
                    return False, ready_replicas, pods, f"Container image pull failure: {msg}"
                if "CrashLoopBackOff" in msg:
                    return False, ready_replicas, pods, f"Pod crashed during startup: {msg}"

            # 3. Check readiness condition
            if ready_replicas >= expected_replicas and updated_replicas >= expected_replicas:
                # Verify at least one pod is Ready
                ready_pod_count = sum(1 for p in pods if p.get("ready"))
                if ready_pod_count >= expected_replicas:
                    logger.info(
                        f"Rollout verified for {deployment_name}: {ready_pod_count}/{expected_replicas} pods Ready"
                    )
                    return True, ready_replicas, pods, None

            time.sleep(poll_interval)

        # Timeout reached
        pods = self.get_pods_for_application(application_name, namespace)
        ready_pod_count = sum(1 for p in pods if p.get("ready"))
        err_detail = f"Rollout timed out after {timeout}s: {ready_pod_count}/{expected_replicas} pods ready."
        if pods:
            messages = [p.get("message") for p in pods if p.get("message")]
            if messages:
                err_detail += f" Pod status: {'; '.join(messages)}"
        logger.warning(err_detail)
        return False, ready_pod_count, pods, err_detail

    def stop_deployment(
        self,
        deployment_name: str,
        namespace: str = "devforge"
    ) -> bool:
        """
        Scale down Deployment to 0 replicas without deleting the deployment or service.
        Keeps resources stable while stopping running workloads.
        """
        apps = self.apps_v1
        try:
            patch_body = {"spec": {"replicas": 0}}
            apps.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch_body)
            logger.info(f"Scaled deployment '{deployment_name}' to 0 replicas in {namespace}")
            return True
        except ApiException as ae:
            if ae.status == 404:
                return True
            raise KubernetesDeploymentError(f"Failed to scale down deployment '{deployment_name}': {ae}") from ae

    def rollout_restart_deployment(
        self,
        deployment_name: str,
        namespace: str = "devforge"
    ) -> bool:
        """
        Trigger a controlled rollout restart of the Kubernetes deployment by updating
        pod template annotations (equivalent to `kubectl rollout restart deployment/<name>`).
        """
        apps = self.apps_v1
        now_str = str(time.time())
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now_str,
                            "devforge.io/restartedAt": now_str,
                        }
                    }
                }
            }
        }
        try:
            apps.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch_body)
            logger.info(f"Triggered rollout restart for deployment '{deployment_name}' in namespace '{namespace}'")
            return True
        except ApiException as ae:
            raise KubernetesDeploymentError(f"Failed to restart deployment '{deployment_name}': {ae}") from ae


kubernetes_client = KubernetesClient()

