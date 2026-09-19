import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.remediation import RemediationEvent, RemediationExecution
from app.services.kubernetes.kubernetes_client import kubernetes_client
from app.services.kubernetes.deployment_service import DeploymentService
from app.services.remediation.exceptions import ActionExecutionError

logger = logging.getLogger("devforge.remediation.action")


class RemediationActionService:
    """
    Executes controlled, scoped, idempotent remediation actions from a strict allowlist.
    Never executes arbitrary commands, deletes namespaces, or destroys infrastructure.
    """

    ALLOWED_ACTIONS = {
        "KUBERNETES_ROLLOUT_RESTART",
        "KUBERNETES_REDEPLOY",
        "ARGOCD_SYNC",
        "RETRY_TRANSIENT_OPERATION",
    }

    def __init__(self):
        self._deployment_service = DeploymentService()

    def execute_action(
        self,
        action: str,
        event: RemediationEvent,
        execution: RemediationExecution,
        db: Session
    ) -> Dict[str, Any]:
        """
        Execute an allowlisted remediation action.
        Returns execution result metadata.
        """
        if action not in self.ALLOWED_ACTIONS:
            raise ActionExecutionError(
                f"Action '{action}' is rejected: not in the strict remediation allowlist."
            )

        app = db.query(Application).filter(Application.id == event.application_id).first()
        if not app:
            raise ActionExecutionError(f"Target application #{event.application_id} not found in database.")

        logger.info(
            f"Executing remediation action '{action}' for app '{app.name}' "
            f"(Env: {event.environment_id}, Event #{event.id}, Attempt #{execution.attempt})"
        )

        if action == "KUBERNETES_ROLLOUT_RESTART":
            return self._rollout_restart(app, event, db)
        elif action == "KUBERNETES_REDEPLOY":
            return self._redeploy(app, event, db)
        elif action == "ARGOCD_SYNC":
            return self._sync_argocd(app, event, db)
        elif action == "RETRY_TRANSIENT_OPERATION":
            return self._retry_transient(app, event, db)
        else:
            raise ActionExecutionError(f"Unhandled action implementation: '{action}'")

    def _rollout_restart(
        self,
        app: Application,
        event: RemediationEvent,
        db: Session
    ) -> Dict[str, Any]:
        """Perform a controlled Kubernetes rollout restart of the application's deployment."""
        k8s_deploy = (
            db.query(KubernetesDeployment)
            .filter(
                KubernetesDeployment.application_id == app.id,
                KubernetesDeployment.environment == event.environment_id,
            )
            .first()
        )
        deployment_name = k8s_deploy.deployment_name if k8s_deploy else f"devforge-{app.slug}"
        namespace = k8s_deploy.namespace if k8s_deploy else "devforge"

        try:
            kubernetes_client.rollout_restart_deployment(
                deployment_name=deployment_name,
                namespace=namespace,
            )
            return {
                "action": "KUBERNETES_ROLLOUT_RESTART",
                "deployment_name": deployment_name,
                "namespace": namespace,
                "status": "INITIATED",
                "message": f"Triggered rolling update for deployment '{deployment_name}' in namespace '{namespace}'",
            }
        except Exception as e:
            logger.error(f"Rollout restart failed for {app.name}: {e}")
            raise ActionExecutionError(f"Kubernetes rollout restart failed: {str(e)}") from e

    def _redeploy(
        self,
        app: Application,
        event: RemediationEvent,
        db: Session
    ) -> Dict[str, Any]:
        """Redeploy application manifests and rolling update."""
        try:
            deployment = self._deployment_service.deploy(
                application_id=app.id,
                db=db,
                environment=event.environment_id,
                replicas=1,
            )
            return {
                "action": "KUBERNETES_REDEPLOY",
                "deployment_name": deployment.deployment_name,
                "namespace": deployment.namespace,
                "status": "INITIATED",
                "message": f"Initiated fresh deployment for '{app.name}' on {event.environment_id}",
            }
        except Exception as e:
            logger.error(f"Redeploy failed for {app.name}: {e}")
            raise ActionExecutionError(f"Kubernetes redeploy failed: {str(e)}") from e

    def _sync_argocd(
        self,
        app: Application,
        event: RemediationEvent,
        db: Session
    ) -> Dict[str, Any]:
        """Synchronize GitOps application state via Argo CD."""
        try:
            from app.models.gitops_application import GitOpsApplication
            from app.services.argocd.sync_service import gitops_sync_service

            gitops_app = (
                db.query(GitOpsApplication)
                .filter(GitOpsApplication.application_id == app.id)
                .first()
            )
            if not gitops_app:
                # If GitOps is not configured for this application, fallback safely to rollout restart
                logger.warning(
                    f"GitOps application record not found for {app.name}. Falling back to KUBERNETES_ROLLOUT_RESTART."
                )
                return self._rollout_restart(app, event, db)

            op = gitops_sync_service.queue_operation(
                gitops_application_id=gitops_app.id,
                operation_type="SYNC",
                db=db,
                details=f"Automated self-healing sync triggered by event #{event.id} ({event.event_type})",
            )
            # Execute synchronously in remediation worker
            processed = gitops_sync_service.execute_operation(op.id, db)
            return {
                "action": "ARGOCD_SYNC",
                "gitops_application": gitops_app.argocd_application_name,
                "operation_id": op.id,
                "status": processed.status if processed else "COMPLETED",
                "message": f"Argo CD sync operation #{op.id} executed for {gitops_app.argocd_application_name}",
            }
        except Exception as e:
            logger.error(f"Argo CD sync failed for {app.name}: {e}")
            raise ActionExecutionError(f"Argo CD synchronization failed: {str(e)}") from e

    def _retry_transient(
        self,
        app: Application,
        event: RemediationEvent,
        db: Session
    ) -> Dict[str, Any]:
        """Retry a transient failure or stuck deployment."""
        k8s_deploy = (
            db.query(KubernetesDeployment)
            .filter(
                KubernetesDeployment.application_id == app.id,
                KubernetesDeployment.environment == event.environment_id,
            )
            .first()
        )
        if k8s_deploy and k8s_deploy.status in ("FAILED", "DEPLOYING"):
            k8s_deploy.status = "DEPLOYING"
            k8s_deploy.error_message = None
            db.commit()
            return self._redeploy(app, event, db)

        return self._rollout_restart(app, event, db)


action_service = RemediationActionService()
