import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.gitops_application import GitOpsApplication
from app.models.activity import Activity
from app.services.argocd.argocd_client import argocd_client, ArgoCDClient
from app.services.argocd.manifest_service import gitops_manifest_service, GitOpsManifestService
from app.services.argocd.exceptions import (
    ArgoCDError,
    ArgoCDUnavailableError,
    ArgoCDApplicationNotFoundError
)

logger = logging.getLogger("devforge.services.argocd.application")

def utcnow():
    return datetime.now(timezone.utc)

class GitOpsApplicationService:
    """
    High-level service managing GitOps applications, bridging PostgreSQL state,
    filesystem manifest topologies, GitHub repositories, and Argo CD CRs.
    """

    def __init__(
        self,
        client: Optional[ArgoCDClient] = None,
        manifest_service: Optional[GitOpsManifestService] = None,
    ):
        self.client = client or argocd_client
        self.manifest_service = manifest_service or gitops_manifest_service
        self.gitops_repo_owner = os.getenv("GITHUB_OWNER", "sripriyancsbs")
        self.gitops_repo_name = os.getenv("GITOPS_REPO_NAME", "devforge-gitops")
        self.default_repo_url = f"https://github.com/{self.gitops_repo_owner}/{self.gitops_repo_name}.git"

    def enable_gitops(
        self,
        application_id: int,
        db: Session,
        git_repository: Optional[str] = None,
        target_revision: str = "main",
        environment: str = "development",
        auto_sync: bool = False,
        self_heal: bool = False,
        image_tag: Optional[str] = None,
        replicas: Optional[int] = None,
    ) -> GitOpsApplication:
        """
        Enable GitOps for an application:
        1. Generates local Kustomize manifests (base + overlay)
        2. Creates/updates Argo CD Application Custom Resource
        3. Upserts GitOpsApplication record in PostgreSQL
        4. Emits Activity audit log entry
        """
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise ValueError(f"Application with ID {application_id} not found.")

        app_slug = application.slug or application.name.lower().replace(" ", "-")
        argocd_app_name = f"devforge-{app_slug}"
        target_path = f"gitops/applications/{app_slug}/overlays/{environment}"
        repo_url = git_repository or (
            "https://github.com/sripriyancsbs/DevForge.git" if "devforge-org" in (application.repository_url or "")
            else (application.repository_url or "https://github.com/sripriyancsbs/DevForge.git")
        )

        # 1. Write manifests to disk
        self.manifest_service.write_manifests_to_disk(
            application=application,
            environment=environment,
            image_tag=image_tag or application.image_tag,
            replicas=replicas or application.replicas
        )

        # 2. Create or update Argo CD Application CR in Kubernetes (if Argo CD is active)
        live_sync = "UNKNOWN"
        live_health = "UNKNOWN"
        try:
            if self.client.is_available():
                argo_app = self.client.create_or_update_application(
                    name=argocd_app_name,
                    repo_url=repo_url,
                    path=target_path,
                    target_revision=target_revision,
                    dest_namespace="devforge",
                    auto_sync=auto_sync,
                    self_heal=self_heal,
                )
                live_sync = argo_app.get("sync_status", "UNKNOWN")
                live_health = argo_app.get("health_status", "UNKNOWN")
        except Exception as e:
            logger.warning(f"Argo CD CR creation deferred or failed: {e}")
            live_sync = "UNKNOWN"

        # 3. Upsert GitOpsApplication record
        gitops_app = db.query(GitOpsApplication).filter(GitOpsApplication.application_id == application_id).first()
        if not gitops_app:
            gitops_app = GitOpsApplication(
                application_id=application_id,
                argocd_application_name=argocd_app_name,
                git_repository=repo_url,
                git_path=target_path,
                target_revision=target_revision,
                namespace="devforge",
                sync_status=live_sync,
                health_status=live_health,
                auto_sync_enabled=auto_sync,
                self_heal_enabled=self_heal,
                last_synced_at=utcnow(),
                manifest_version=1,
            )
            db.add(gitops_app)
        else:
            gitops_app.argocd_application_name = argocd_app_name
            gitops_app.git_repository = repo_url
            gitops_app.git_path = target_path
            gitops_app.target_revision = target_revision
            gitops_app.sync_status = live_sync if live_sync != "UNKNOWN" else gitops_app.sync_status
            gitops_app.health_status = live_health if live_health != "UNKNOWN" else gitops_app.health_status
            gitops_app.auto_sync_enabled = auto_sync
            gitops_app.self_heal_enabled = self_heal
            gitops_app.manifest_version += 1
            gitops_app.updated_at = utcnow()

        # 4. Activity Log
        activity = Activity(
            actor="operator",
            action="gitops_enabled",
            target=application.name,
            target_type="gitops",
            status="completed",
            details=f"GitOps enabled for '{application.name}' via Argo CD ({argocd_app_name})",
            created_at=utcnow(),
        )
        db.add(activity)
        db.commit()
        db.refresh(gitops_app)

        logger.info(f"GitOps enabled for application '{application.name}' (ID: {application_id})")
        return gitops_app

    def get_gitops_application(self, application_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get GitOps application status, combining PostgreSQL metadata with live Argo CD state.
        """
        gitops_app = db.query(GitOpsApplication).filter(GitOpsApplication.application_id == application_id).first()
        if not gitops_app:
            return None

        # Fetch live state from Argo CD if available
        live_data = {}
        try:
            if self.client.is_available():
                live_data = self.client.get_application(gitops_app.argocd_application_name)
                # Update PostgreSQL with live reconciliation state
                if live_data.get("sync_status"):
                    gitops_app.sync_status = live_data["sync_status"]
                if live_data.get("health_status"):
                    gitops_app.health_status = live_data["health_status"]
                if live_data.get("sync_message"):
                    gitops_app.sync_message = live_data["sync_message"]
                gitops_app.updated_at = utcnow()
                db.commit()
                db.refresh(gitops_app)
        except Exception as e:
            logger.debug(f"Could not refresh live Argo CD state for '{gitops_app.argocd_application_name}': {e}")

        app = db.query(Application).filter(Application.id == application_id).first()
        app_name = app.name if app else gitops_app.argocd_application_name

        return {
            "id": gitops_app.id,
            "application_id": gitops_app.application_id,
            "application_name": app_name,
            "argocd_application_name": gitops_app.argocd_application_name,
            "git_repository": gitops_app.git_repository,
            "git_path": gitops_app.git_path,
            "target_revision": gitops_app.target_revision,
            "namespace": gitops_app.namespace,
            "sync_status": gitops_app.sync_status,
            "health_status": gitops_app.health_status,
            "auto_sync_enabled": gitops_app.auto_sync_enabled,
            "self_heal_enabled": gitops_app.self_heal_enabled,
            "last_synced_at": gitops_app.last_synced_at.isoformat() if gitops_app.last_synced_at else None,
            "last_sync_revision": gitops_app.last_sync_revision or live_data.get("sync_revision"),
            "sync_message": gitops_app.sync_message or live_data.get("sync_message"),
            "drift_count": live_data.get("drift_count", 0),
            "drifted_resources": live_data.get("drifted_resources", []),
            "created_at": gitops_app.created_at.isoformat() if gitops_app.created_at else None,
            "updated_at": gitops_app.updated_at.isoformat() if gitops_app.updated_at else None,
        }

    def list_gitops_applications(self, db: Session) -> List[Dict[str, Any]]:
        """List all GitOps managed applications with live status."""
        apps = db.query(GitOpsApplication).order_by(GitOpsApplication.created_at.desc()).all()
        results = []
        for a in apps:
            data = self.get_gitops_application(a.application_id, db)
            if data:
                results.append(data)
        return results

gitops_application_service = GitOpsApplicationService()
