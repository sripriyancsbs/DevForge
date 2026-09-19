import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.container_image import ContainerImage
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.activity import Activity
from app.services.kubernetes.manifest_generator import manifest_generator
from app.services.kubernetes.kubernetes_client import kubernetes_client
from app.services.kubernetes.exceptions import (
    KubernetesError,
    KubernetesClusterUnavailableError,
    KubernetesManifestError,
)

logger = logging.getLogger("devforge.deployment_service")


def utcnow():
    return datetime.now(timezone.utc)


class DeploymentService:
    """
    Orchestrates Kubernetes deployments for DevForge applications.
    Manages manifest generation, cluster application, rollout verification,
    database state persistence, and activity auditing.
    """

    def _record_activity(
        self,
        db: Session,
        actor: str,
        action: str,
        target: str,
        status: str,
        details: str,
    ) -> None:
        """Helper to record audit activity events."""
        activity = Activity(
            actor=actor,
            action=action,
            target=target,
            target_type="deployment",
            status=status,
            details=details,
            created_at=utcnow(),
        )
        db.add(activity)
        db.commit()

    def deploy(
        self,
        application_id: int,
        db: Session,
        image_tag: Optional[str] = None,
        environment: str = "development",
        replicas: int = 1,
        port: Optional[int] = None,
    ) -> KubernetesDeployment:
        """
        Execute full deployment workflow:
        1. Resolve Application and Container Image (from Phase 5)
        2. Ensure Kubernetes Namespace and GHCR pull Secret
        3. Generate valid Kubernetes manifests (Deployment, Service, ConfigMap)
        4. Apply manifests to cluster idempotently
        5. Verify rollout (Pods ready, Replicas matched, Service live)
        6. Update PostgreSQL state and emit Activity logs
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application with ID {application_id} not found")

        # 1. Resolve container image
        resolved_repo = app.image_repository
        if not resolved_repo:
            owner = app.repository_owner or settings.GITHUB_OWNER or "devforge"
            resolved_repo = f"ghcr.io/{owner.strip().lower()}/{app.name.strip().lower()}"

        resolved_tag = image_tag
        if not resolved_tag:
            # Query latest image from Phase 5 container_images table
            latest_img = (
                db.query(ContainerImage)
                .filter(ContainerImage.application_id == app.id)
                .order_by(ContainerImage.created_at.desc())
                .first()
            )
            if latest_img and latest_img.image_tag:
                resolved_tag = latest_img.image_tag
            elif app.image_tag:
                resolved_tag = app.image_tag
            else:
                resolved_tag = "latest"

        full_image = f"{resolved_repo}:{resolved_tag}"
        namespace = settings.KUBERNETES_NAMESPACE or "devforge"

        # Record activity: Deployment requested
        self._record_activity(
            db=db,
            actor="user",
            action="Deployment requested",
            target=app.name,
            status="pending",
            details=f"Deployment requested for {app.name} using image {full_image} on environment '{environment}'"
        )

        # Find or create existing deployment record for idempotency
        k8s_deploy = (
            db.query(KubernetesDeployment)
            .filter(
                KubernetesDeployment.application_id == app.id,
                KubernetesDeployment.environment == environment,
            )
            .first()
        )

        resolved_port = manifest_generator.resolve_port(app.template, port or app.port)

        if not k8s_deploy:
            k8s_deploy = KubernetesDeployment(
                application_id=app.id,
                environment=environment,
                namespace=namespace,
                deployment_name=f"devforge-{app.slug}",
                service_name=f"devforge-{app.slug}-svc",
                image_repository=resolved_repo,
                image_tag=resolved_tag,
                replicas=replicas,
                ready_replicas=0,
                status="DEPLOYING",
                port=resolved_port,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(k8s_deploy)
        else:
            k8s_deploy.image_repository = resolved_repo
            k8s_deploy.image_tag = resolved_tag
            k8s_deploy.replicas = replicas
            k8s_deploy.port = resolved_port
            k8s_deploy.status = "DEPLOYING"
            k8s_deploy.error_message = None
            k8s_deploy.updated_at = utcnow()

        db.commit()
        db.refresh(k8s_deploy)

        # 2. Ensure namespace and image pull secret
        try:
            kubernetes_client.ensure_namespace(namespace)
            pull_secret = kubernetes_client.ensure_image_pull_secret(namespace)
        except Exception as e:
            k8s_deploy.status = "FAILED"
            k8s_deploy.error_message = f"Cluster setup failure: {str(e)}"
            db.commit()
            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment failed",
                target=app.name,
                status="failed",
                details=f"Kubernetes cluster setup error: {str(e)}"
            )
            raise

        # 3. Generate manifests
        try:
            yamls = manifest_generator.generate_manifest_yamls(
                application_name=app.name,
                image=full_image,
                replicas=replicas,
                port=resolved_port,
                template=app.template,
                namespace=namespace,
                environment=environment,
                image_pull_secret=pull_secret,
            )
            k8s_deploy.manifest_yaml = yamls["combined"]
            k8s_deploy.deployment_name = yamls["deployment_name"]
            k8s_deploy.service_name = yamls["service_name"]
            db.commit()

            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Manifest generated",
                target=app.name,
                status="completed",
                details=f"Generated Kubernetes YAML manifests for Deployment {yamls['deployment_name']} and Service {yamls['service_name']}"
            )
        except Exception as e:
            k8s_deploy.status = "FAILED"
            k8s_deploy.error_message = f"Manifest generation failure: {str(e)}"
            db.commit()
            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment failed",
                target=app.name,
                status="failed",
                details=f"Manifest generation error: {str(e)}"
            )
            raise

        # 4. Apply manifests
        self._record_activity(
            db=db,
            actor="devforge.k8s",
            action="Kubernetes deployment started",
            target=app.name,
            status="in_progress",
            details=f"Applying manifests to namespace {namespace} for {yamls['deployment_name']}"
        )

        try:
            # Apply ConfigMap
            cm_dict = manifest_generator.generate_configmap_dict(app.name, namespace, environment)
            kubernetes_client.apply_configmap(cm_dict, namespace)

            # Apply Service
            svc_dict = manifest_generator.generate_service_dict(
                application_name=app.name,
                port=resolved_port,
                service_type="NodePort",
                namespace=namespace,
                environment=environment,
            )
            svc_name, node_port = kubernetes_client.apply_service(svc_dict, namespace)
            k8s_deploy.node_port = node_port

            # Apply Deployment
            dep_dict = manifest_generator.generate_deployment_dict(
                application_name=app.name,
                image=full_image,
                replicas=replicas,
                port=resolved_port,
                template=app.template,
                namespace=namespace,
                environment=environment,
                image_pull_secret=pull_secret,
                config_map_name=cm_dict["metadata"]["name"],
            )
            dep_name = kubernetes_client.apply_deployment(dep_dict, namespace)

            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment created",
                target=app.name,
                status="in_progress",
                details=f"Applied Deployment {dep_name} and Service {svc_name} (NodePort: {node_port})"
            )
            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Pods starting",
                target=app.name,
                status="in_progress",
                details=f"Waiting for {replicas} pod replica(s) to become Ready"
            )
        except Exception as e:
            k8s_deploy.status = "FAILED"
            k8s_deploy.error_message = f"Failed to apply Kubernetes resources: {str(e)}"
            db.commit()
            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment failed",
                target=app.name,
                status="failed",
                details=f"Resource application failed: {str(e)}"
            )
            raise

        # 5. Rollout verification
        timeout = settings.KUBERNETES_ROLLOUT_TIMEOUT
        is_ready, ready_reps, pods, err_msg = kubernetes_client.verify_rollout(
            deployment_name=dep_name,
            application_name=app.name,
            expected_replicas=replicas,
            namespace=namespace,
            timeout=timeout,
        )

        k8s_deploy.ready_replicas = ready_reps
        if is_ready:
            k8s_deploy.status = "RUNNING"
            k8s_deploy.error_message = None
            app.status = "healthy"
            app.last_deployment_at = utcnow()
            db.commit()

            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment ready",
                target=app.name,
                status="completed",
                details=f"Rollout complete: {ready_reps}/{replicas} pods Ready. Application is RUNNING."
            )
        else:
            k8s_deploy.status = "FAILED"
            k8s_deploy.error_message = err_msg or "Rollout failed to reach ready state"
            db.commit()

            self._record_activity(
                db=db,
                actor="devforge.k8s",
                action="Deployment failed",
                target=app.name,
                status="failed",
                details=k8s_deploy.error_message
            )

        try:
            from app.core.metrics import record_deployment_metric
            record_deployment_metric(environment, k8s_deploy.status)
        except Exception:
            pass

        db.refresh(k8s_deploy)
        return k8s_deploy

    def redeploy(
        self,
        application_id: int,
        db: Session,
        image_tag: Optional[str] = None,
        replicas: Optional[int] = None,
    ) -> KubernetesDeployment:
        """Redeploy application, re-verifying rollout and recording redeployment activity."""
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application with ID {application_id} not found")

        current = (
            db.query(KubernetesDeployment)
            .filter(KubernetesDeployment.application_id == app.id)
            .order_by(KubernetesDeployment.created_at.desc())
            .first()
        )

        tag = image_tag or (current.image_tag if current else None)
        reps = replicas or (current.replicas if current else 1)
        env = current.environment if current else "development"

        self._record_activity(
            db=db,
            actor="user",
            action="Deployment redeployed",
            target=app.name,
            status="pending",
            details=f"Redeployment initiated for {app.name} (tag: {tag or 'latest'}, replicas: {reps})"
        )

        return self.deploy(
            application_id=application_id,
            db=db,
            image_tag=tag,
            environment=env,
            replicas=reps,
            port=current.port if current else None,
        )

    def stop(
        self,
        application_id: int,
        db: Session,
    ) -> KubernetesDeployment:
        """Stop running deployment by scaling replicas to 0."""
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application with ID {application_id} not found")

        current = (
            db.query(KubernetesDeployment)
            .filter(KubernetesDeployment.application_id == app.id)
            .order_by(KubernetesDeployment.created_at.desc())
            .first()
        )
        if not current:
            raise ValueError(f"No active deployment found for application {app.name}")

        kubernetes_client.stop_deployment(
            deployment_name=current.deployment_name,
            namespace=current.namespace,
        )

        current.status = "STOPPED"
        current.ready_replicas = 0
        current.updated_at = utcnow()
        db.commit()
        db.refresh(current)

        self._record_activity(
            db=db,
            actor="user",
            action="Deployment stopped",
            target=app.name,
            status="completed",
            details=f"Deployment {current.deployment_name} stopped (scaled to 0 replicas)"
        )
        return current

    def get_deployment_status(
        self,
        application_id: int,
        db: Session,
    ) -> Optional[Dict[str, Any]]:
        """
        Get deployment metadata along with real-time Kubernetes Pod statuses.
        Does NOT return fake or static statuses.
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            return None

        current = (
            db.query(KubernetesDeployment)
            .filter(KubernetesDeployment.application_id == app.id)
            .order_by(KubernetesDeployment.created_at.desc())
            .first()
        )
        if not current:
            return None

        # Fetch real-time pod statuses from cluster if available
        pods = []
        try:
            pods = kubernetes_client.get_pods_for_application(app.name, current.namespace)
        except Exception as e:
            logger.warning(f"Could not fetch real-time pods for {app.name}: {e}")

        # Compute service access URL
        service_url = None
        if current.node_port:
            service_url = f"http://localhost:{current.node_port}"
        elif current.port:
            service_url = f"http://localhost:{current.port}"

        return {
            "id": current.id,
            "application_id": current.application_id,
            "application_name": app.name,
            "environment": current.environment,
            "namespace": current.namespace,
            "deployment_name": current.deployment_name,
            "service_name": current.service_name,
            "image": f"{current.image_repository}:{current.image_tag}",
            "image_repository": current.image_repository,
            "image_tag": current.image_tag,
            "replicas": current.replicas,
            "ready_replicas": current.ready_replicas,
            "status": current.status,
            "port": current.port,
            "node_port": current.node_port,
            "service_url": service_url,
            "manifest_yaml": current.manifest_yaml,
            "error_message": current.error_message,
            "pods": pods,
            "created_at": current.created_at,
            "updated_at": current.updated_at,
        }


deployment_service = DeploymentService()
