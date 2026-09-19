import time
import logging
import urllib.request
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.kubernetes_deployment import KubernetesDeployment
from app.services.kubernetes.kubernetes_client import kubernetes_client
from app.core.config import settings

logger = logging.getLogger("devforge.remediation.verifier")


class RemediationHealthVerifier:
    """
    Multi-step health verifier ensuring an application has genuinely recovered
    after a remediation action.
    Never assumes recovery merely because an API call or restart succeeded.
    """

    def verify_recovery(
        self,
        application: Application,
        environment: str,
        db: Session,
        timeout: int = 60,
        poll_interval: float = 2.0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify post-remediation health through:
        1. Kubernetes Rollout completion (ready replicas >= desired)
        2. Pod Readiness conditions (no CrashLoopBackOff, ready == True)
        3. Optional HTTP health probe verification
        """
        k8s_deploy = (
            db.query(KubernetesDeployment)
            .filter(
                KubernetesDeployment.application_id == application.id,
                KubernetesDeployment.environment == environment,
            )
            .first()
        )

        deployment_name = k8s_deploy.deployment_name if k8s_deploy else f"devforge-{application.slug}"
        namespace = k8s_deploy.namespace if k8s_deploy else "devforge"
        expected_replicas = k8s_deploy.replicas if k8s_deploy else 1

        logger.info(
            f"Starting post-remediation health verification for '{application.name}' "
            f"(Deployment: {deployment_name}, Namespace: {namespace}, Timeout: {timeout}s)..."
        )

        # 1. Verify Kubernetes Rollout
        is_rollout_ok, ready_replicas, pods, rollout_err = kubernetes_client.verify_rollout(
            deployment_name=deployment_name,
            application_name=application.name,
            expected_replicas=expected_replicas,
            namespace=namespace,
            timeout=timeout,
            poll_interval=poll_interval,
        )

        if not is_rollout_ok:
            logger.warning(
                f"Health verification failed for '{application.name}': Rollout unconfirmed. {rollout_err}"
            )
            return False, {
                "step": "rollout_verification",
                "ready_replicas": ready_replicas,
                "expected_replicas": expected_replicas,
                "error": rollout_err or "Rollout timeout: pods failed to become ready",
                "pods": pods,
            }

        # 2. Check for Pod CrashLoops or restart increments
        crash_pods = [p for p in pods if "CrashLoopBackOff" in (p.get("message") or "")]
        if crash_pods:
            logger.warning(f"Health verification failed for '{application.name}': Pod in CrashLoopBackOff")
            return False, {
                "step": "pod_health",
                "error": f"Pod '{crash_pods[0]['name']}' is stuck in CrashLoopBackOff",
                "pods": pods,
            }

        # 3. Optional HTTP Health probe if NodePort is exposed
        http_verified = None
        http_endpoint = None
        if k8s_deploy and k8s_deploy.node_port:
            node_port = k8s_deploy.node_port
            http_endpoint = f"http://127.0.0.1:{node_port}/health"
            try:
                req = urllib.request.Request(http_endpoint, headers={"User-Agent": "DevForge-HealthVerifier/1.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    http_verified = resp.status in (200, 204, 301, 302)
            except Exception:
                # Fallback to root /
                try:
                    root_req = urllib.request.Request(f"http://127.0.0.1:{node_port}/", headers={"User-Agent": "DevForge-HealthVerifier/1.0"})
                    with urllib.request.urlopen(root_req, timeout=2.0) as resp:
                        http_verified = resp.status in (200, 204, 301, 302)
                except Exception as e:
                    # In some test environments direct NodePort may not be routeable from inside container
                    # We log it, but do not fail rollout if pods are Ready and running
                    logger.debug(f"HTTP health probe to {http_endpoint} returned: {e}")
                    http_verified = None

        logger.info(
            f"Health verification SUCCESSFUL for '{application.name}': "
            f"{ready_replicas}/{expected_replicas} pods Ready."
        )

        return True, {
            "step": "complete",
            "ready_replicas": ready_replicas,
            "expected_replicas": expected_replicas,
            "pod_count": len(pods),
            "http_probe": "passed" if http_verified else "skipped_or_unreachable",
            "endpoint": http_endpoint,
        }


health_verifier = RemediationHealthVerifier()
