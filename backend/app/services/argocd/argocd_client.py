import os
import json
import logging
import urllib.request
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.services.argocd.exceptions import (
    ArgoCDError,
    ArgoCDUnavailableError,
    ArgoCDApplicationNotFoundError,
    ArgoCDSyncError,
)

logger = logging.getLogger("devforge.services.argocd.client")

GITOPS_GROUP = "argoproj.io"
GITOPS_VERSION = "v1alpha1"
GITOPS_PLURAL = "applications"
ARGOCD_NAMESPACE = "argocd"

class ArgoCDClient:
    """
    Client for Argo CD orchestrating Application Custom Resources and querying health/sync status.
    Interacts via Kubernetes CustomObjectsApi with fallback to Argo CD REST API.
    """

    def __init__(self):
        self.server_url = os.getenv("ARGOCD_SERVER_URL", "http://localhost:8080")
        self._init_k8s_client()

    def _init_k8s_client(self):
        """Initialize Kubernetes API client from kubeconfig or in-cluster config."""
        try:
            config.load_incluster_config()
            self._k8s_api = client.CustomObjectsApi()
            self._k8s_ready = True
        except Exception:
            try:
                config.load_kube_config()
                self._k8s_api = client.CustomObjectsApi()
                self._k8s_ready = True
            except Exception as e:
                logger.warning(f"Could not initialize Kubernetes client for Argo CD: {e}")
                self._k8s_api = None
                self._k8s_ready = False

    def is_available(self) -> bool:
        """Check if Argo CD is installed and healthy in the cluster."""
        if not self._k8s_ready or not self._k8s_api:
            self._init_k8s_client()
            if not self._k8s_ready:
                return False

        try:
            self._k8s_api.list_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
                limit=1,
            )
            return True
        except Exception as e:
            logger.debug(f"Argo CD CRD check failed: {e}")
            return False

    def get_cluster_status(self) -> Dict[str, Any]:
        """Probe Argo CD connectivity and return summary."""
        available = self.is_available()
        version = "v3.5.3"
        try:
            req = urllib.request.Request(f"{self.server_url}/api/version", headers={"User-Agent": "DevForge/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    version = data.get("Version", version)
        except Exception:
            pass

        return {
            "available": available,
            "version": version,
            "server_url": self.server_url,
            "namespace": ARGOCD_NAMESPACE,
        }

    def list_applications(self) -> List[Dict[str, Any]]:
        """List all Argo CD Application custom resources in argocd namespace."""
        if not self.is_available():
            raise ArgoCDUnavailableError("Argo CD is not reachable in the Kubernetes cluster.")

        try:
            res = self._k8s_api.list_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
            )
            items = res.get("items", [])
            return [self._format_app_summary(item) for item in items]
        except ApiException as e:
            raise ArgoCDError(f"Failed to list Argo CD applications: {e.reason}") from e

    def get_application(self, app_name: str) -> Dict[str, Any]:
        """Fetch raw Argo CD Application custom resource by name."""
        if not self.is_available():
            raise ArgoCDUnavailableError("Argo CD is not reachable in the Kubernetes cluster.")

        try:
            raw = self._k8s_api.get_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
                name=app_name,
            )
            return self._format_app_summary(raw)
        except ApiException as e:
            if e.status == 404:
                raise ArgoCDApplicationNotFoundError(f"Argo CD Application '{app_name}' not found.") from e
            raise ArgoCDError(f"Failed to get Argo CD application '{app_name}': {e.reason}") from e

    def create_or_update_application(
        self,
        name: str,
        repo_url: str,
        path: str,
        target_revision: str = "main",
        dest_namespace: str = "devforge",
        dest_server: str = "https://kubernetes.default.svc",
        auto_sync: bool = False,
        self_heal: bool = False,
    ) -> Dict[str, Any]:
        """
        Create or update an Argo CD Application custom resource in Kubernetes.
        Guarantees idempotency: if already exists, updates spec without destroying state.
        """
        if not self.is_available():
            raise ArgoCDUnavailableError("Argo CD is not reachable in the Kubernetes cluster.")

        sync_policy: Dict[str, Any] = {
            "syncOptions": [
                "CreateNamespace=true",
                "ApplyOutOfSyncOnly=true"
            ]
        }
        if auto_sync:
            automated = {"prune": False, "selfHeal": self_heal}
            sync_policy["automated"] = automated

        app_manifest = {
            "apiVersion": f"{GITOPS_GROUP}/{GITOPS_VERSION}",
            "kind": "Application",
            "metadata": {
                "name": name,
                "namespace": ARGOCD_NAMESPACE,
                "labels": {
                    "app.kubernetes.io/managed-by": "devforge-idp",
                    "devforge.io/application": name,
                },
            },
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": repo_url,
                    "targetRevision": target_revision,
                    "path": path,
                },
                "destination": {
                    "server": dest_server,
                    "namespace": dest_namespace,
                },
                "syncPolicy": sync_policy,
            },
        }

        try:
            # Check if exists
            try:
                existing = self._k8s_api.get_namespaced_custom_object(
                    group=GITOPS_GROUP,
                    version=GITOPS_VERSION,
                    namespace=ARGOCD_NAMESPACE,
                    plural=GITOPS_PLURAL,
                    name=name,
                )
                # Update existing spec
                existing["spec"] = app_manifest["spec"]
                updated = self._k8s_api.replace_namespaced_custom_object(
                    group=GITOPS_GROUP,
                    version=GITOPS_VERSION,
                    namespace=ARGOCD_NAMESPACE,
                    plural=GITOPS_PLURAL,
                    name=name,
                    body=existing,
                )
                logger.info(f"Updated existing Argo CD Application '{name}'")
                return self._format_app_summary(updated)
            except ApiException as e:
                if e.status != 404:
                    raise

            # Create new
            created = self._k8s_api.create_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
                body=app_manifest,
            )
            logger.info(f"Created new Argo CD Application '{name}'")
            return self._format_app_summary(created)
        except ApiException as e:
            raise ArgoCDError(f"Failed to create/update Argo CD application '{name}': {e.reason}") from e

    def sync_application(self, name: str, revision: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger an Argo CD synchronization operation by applying an operation payload to the CR.
        """
        if not self.is_available():
            raise ArgoCDUnavailableError("Argo CD is not reachable in the Kubernetes cluster.")

        operation_payload = {
            "operation": {
                "sync": {
                    "revision": revision or "HEAD",
                    "syncOptions": ["CreateNamespace=true"],
                    "prune": False,
                },
                "initiatedBy": {
                    "username": "devforge-operator",
                },
            }
        }

        try:
            updated = self._k8s_api.patch_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
                name=name,
                body=operation_payload,
            )
            logger.info(f"Triggered sync for Argo CD Application '{name}'")
            return self._format_app_summary(updated)
        except ApiException as e:
            raise ArgoCDSyncError(f"Failed to trigger sync for '{name}': {e.reason}") from e

    def refresh_application(self, name: str) -> Dict[str, Any]:
        """
        Trigger a hard reconciliation refresh by annotating the Argo CD Application CR.
        """
        if not self.is_available():
            raise ArgoCDUnavailableError("Argo CD is not reachable in the Kubernetes cluster.")

        patch = {
            "metadata": {
                "annotations": {
                    "argocd.argoproj.io/refresh": "hard"
                }
            }
        }

        try:
            updated = self._k8s_api.patch_namespaced_custom_object(
                group=GITOPS_GROUP,
                version=GITOPS_VERSION,
                namespace=ARGOCD_NAMESPACE,
                plural=GITOPS_PLURAL,
                name=name,
                body=patch,
            )
            logger.info(f"Triggered hard refresh for Argo CD Application '{name}'")
            return self._format_app_summary(updated)
        except ApiException as e:
            raise ArgoCDError(f"Failed to refresh Argo CD application '{name}': {e.reason}") from e

    def _format_app_summary(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Map raw Argo CD CR payload into normalized DevForge GitOps status summary."""
        metadata = raw.get("metadata", {})
        spec = raw.get("spec", {})
        status = raw.get("status", {})

        source = spec.get("source", {})
        destination = spec.get("destination", {})

        sync_info = status.get("sync", {})
        health_info = status.get("health", {})

        # Normalize sync status
        raw_sync = sync_info.get("status", "Unknown")
        if raw_sync == "Synced":
            sync_status = "SYNCED"
        elif raw_sync == "OutOfSync":
            sync_status = "OUT_OF_SYNC"
        elif raw_sync == "Syncing":
            sync_status = "SYNCING"
        else:
            sync_status = "UNKNOWN"

        # Normalize health status
        raw_health = health_info.get("status", "Unknown")
        if raw_health == "Healthy":
            health_status = "HEALTHY"
        elif raw_health == "Progressing":
            health_status = "PROGRESSING"
        elif raw_health == "Degraded":
            health_status = "DEGRADED"
        elif raw_health == "Missing":
            health_status = "MISSING"
        else:
            health_status = "UNKNOWN"

        # Drift extraction
        resources = status.get("resources", [])
        drifted_resources = []
        for r in resources:
            if r.get("status") == "OutOfSync":
                drifted_resources.append({
                    "group": r.get("group", ""),
                    "kind": r.get("kind", ""),
                    "name": r.get("name", ""),
                    "namespace": r.get("namespace", ""),
                    "hook": r.get("hook", False),
                })

        return {
            "name": metadata.get("name"),
            "namespace": destination.get("namespace", "devforge"),
            "git_repository": source.get("repoURL"),
            "git_path": source.get("path"),
            "target_revision": source.get("targetRevision", "main"),
            "sync_status": sync_status,
            "health_status": health_status,
            "sync_revision": sync_info.get("revision"),
            "sync_message": health_info.get("message") or status.get("operationState", {}).get("message"),
            "drift_count": len(drifted_resources),
            "drifted_resources": drifted_resources,
            "auto_sync_enabled": bool(spec.get("syncPolicy", {}).get("automated")),
            "created_at": metadata.get("creationTimestamp"),
        }

argocd_client = ArgoCDClient()
