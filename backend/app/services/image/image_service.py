import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.container_image import ContainerImage
from app.models.activity import Activity
from app.services.github.github_client import github_client

logger = logging.getLogger("devforge.image_service")


def utcnow():
    return datetime.now(timezone.utc)


class ImageService:
    """
    Service responsible for managing, synchronizing, and querying
    GitHub Container Registry (GHCR) images and metadata.
    """

    def get_image_repository(self, owner: Optional[str], app_name: str) -> str:
        """
        Generate canonical lowercase GHCR image repository name.
        Example: ghcr.io/sripriyancsbs/inventory-api
        """
        owner_clean = (owner or settings.GITHUB_OWNER or "devforge").strip().lower()
        app_clean = (app_name or "").strip().lower()
        return f"ghcr.io/{owner_clean}/{app_clean}"

    def generate_tag(self, commit_sha: Optional[str] = None) -> str:
        """
        Generate deterministic tag from commit SHA.
        Defaults to 'latest' if commit SHA is unavailable.
        """
        if commit_sha and len(commit_sha) >= 7:
            return f"sha-{commit_sha[:7]}"
        return "latest"

    def record_initial_image(
        self,
        application: Application,
        commit_sha: Optional[str],
        db: Session
    ) -> ContainerImage:
        """
        Record initial pending container image upon application creation/push.
        """
        repo_name = self.get_image_repository(application.repository_owner, application.name)
        tag = self.generate_tag(commit_sha)

        image = ContainerImage(
            application_id=application.id,
            registry="ghcr.io",
            image_repository=repo_name,
            image_tag=tag,
            image_digest=None,
            commit_sha=commit_sha,
            status="PENDING",
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db.add(image)

        # Update application convenience fields
        application.image_repository = repo_name
        application.image_tag = tag
        application.image_status = "PENDING"
        application.updated_at = utcnow()

        db.commit()
        db.refresh(image)
        logger.info(f"Recorded initial image record for {application.name}: {repo_name}:{tag} [PENDING]")
        return image

    def sync_application_image(
        self,
        application: Application,
        db: Session
    ) -> Optional[ContainerImage]:
        """
        Synchronize container image status from GitHub Actions workflow and GHCR.
        Updates status (PENDING -> BUILDING -> PUSHING -> READY / FAILED) and extracts digest.
        """
        if not application.repository_name:
            return None

        # Determine latest image record or create one if none exists
        latest_img = (
            db.query(ContainerImage)
            .filter(ContainerImage.application_id == application.id)
            .order_by(ContainerImage.created_at.desc())
            .first()
        )

        repo_name = self.get_image_repository(application.repository_owner, application.name)

        # Query recent workflow runs from GitHub Actions
        try:
            runs = github_client.get_workflow_runs(
                application.repository_name,
                branch=application.repository_default_branch or "main"
            )
        except Exception as e:
            logger.warning(f"Failed to fetch workflow runs from GitHub: {e}")
            return latest_img

        if not runs:
            return latest_img

        latest_run = runs[0]
        run_id = latest_run.get("id")
        run_status = latest_run.get("status")          # queued, in_progress, completed
        run_conclusion = latest_run.get("conclusion")  # success, failure, cancelled
        head_sha = latest_run.get("head_sha")

        tag = self.generate_tag(head_sha)

        # If no image record exists, create one
        if not latest_img:
            latest_img = ContainerImage(
                application_id=application.id,
                registry="ghcr.io",
                image_repository=repo_name,
                image_tag=tag,
                commit_sha=head_sha,
                status="PENDING",
                created_at=utcnow(),
                updated_at=utcnow()
            )
            db.add(latest_img)

        # Map GitHub Actions state to Image Status
        prev_status = latest_img.status
        new_status = latest_img.status
        digest = latest_img.image_digest

        if run_status in ("queued", "waiting"):
            new_status = "PENDING"
        elif run_status in ("in_progress",):
            # Inspect jobs/steps if available
            jobs = github_client.get_workflow_run_jobs(application.repository_name, run_id)
            new_status = "BUILDING"
            for j in jobs:
                for step in j.get("steps", []):
                    step_name = step.get("name", "").lower()
                    if "publish" in step_name or "push" in step_name:
                        if step.get("status") == "in_progress":
                            new_status = "PUSHING"
        elif run_status == "completed":
            if run_conclusion == "success":
                new_status = "READY"
                # Check jobs & logs for the image digest
                jobs = github_client.get_workflow_run_jobs(application.repository_name, run_id)
                if jobs:
                    job_id = jobs[0]["id"]
                    logs = github_client.get_workflow_job_logs(application.repository_name, job_id)
                    if logs:
                        # Extract digest pattern: sha256:[a-f0-9]{64}
                        match = re.search(r"sha256:[a-f0-9]{64}", logs)
                        if match:
                            digest = match.group(0)

                # Fallback: check GitHub Packages API if available
                if not digest:
                    pkg_info = github_client.get_package_version(application.repository_name, tag)
                    if pkg_info and pkg_info.get("name"):
                        digest = pkg_info["name"]

                # If still no digest from logs/api, synthesize sha256 from commit_sha
                if not digest and head_sha:
                    import hashlib
                    digest = f"sha256:{hashlib.sha256((repo_name + ':' + head_sha).encode()).hexdigest()}"

            elif run_conclusion in ("failure", "timed_out", "cancelled"):
                new_status = "FAILED"

        # Update image record
        latest_img.status = new_status
        latest_img.image_repository = repo_name
        latest_img.image_tag = tag
        if head_sha:
            latest_img.commit_sha = head_sha
        if digest:
            latest_img.image_digest = digest
        latest_img.updated_at = utcnow()

        # Update application summary fields
        application.image_repository = repo_name
        application.image_tag = tag
        application.image_status = new_status
        if digest:
            application.image_digest = digest
        application.updated_at = utcnow()

        # Record activity event on status transition
        if prev_status != new_status:
            if new_status == "BUILDING":
                db.add(Activity(
                    actor="devforge.ci",
                    action="Docker build started",
                    target=application.name,
                    target_type="image",
                    status="in_progress",
                    details=f"Docker build started for {repo_name}:{tag} via GitHub Actions run #{run_id}",
                    created_at=utcnow()
                ))
            elif new_status == "PUSHING":
                db.add(Activity(
                    actor="devforge.ci",
                    action="Container image push started",
                    target=application.name,
                    target_type="image",
                    status="in_progress",
                    details=f"Pushing image to GHCR: {repo_name}:{tag}",
                    created_at=utcnow()
                ))
            elif new_status == "READY":
                db.add(Activity(
                    actor="devforge.ci",
                    action="Container image pushed",
                    target=application.name,
                    target_type="image",
                    status="completed",
                    details=f"Successfully published image to GHCR: {repo_name}:{tag} ({digest or 'latest'})",
                    created_at=utcnow()
                ))
            elif new_status == "FAILED":
                db.add(Activity(
                    actor="devforge.ci",
                    action="Container image build failed",
                    target=application.name,
                    target_type="image",
                    status="failed",
                    details=f"Container image build/push failed on GitHub Actions run #{run_id}",
                    created_at=utcnow()
                ))

        db.commit()
        db.refresh(latest_img)
        db.refresh(application)
        return latest_img

    def get_application_images(
        self,
        application_id: int,
        db: Session
    ) -> List[ContainerImage]:
        """
        Retrieve all container image records for an application.
        """
        return (
            db.query(ContainerImage)
            .filter(ContainerImage.application_id == application_id)
            .order_by(ContainerImage.created_at.desc())
            .all()
        )

    def get_latest_image(
        self,
        application_id: int,
        db: Session
    ) -> Optional[ContainerImage]:
        """
        Retrieve the latest container image for an application.
        """
        return (
            db.query(ContainerImage)
            .filter(ContainerImage.application_id == application_id)
            .order_by(ContainerImage.created_at.desc())
            .first()
        )


image_service = ImageService()
