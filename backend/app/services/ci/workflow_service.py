import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import yaml
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.activity import Activity
from app.services.ci.workflow_generator import workflow_generator
from app.services.ci.exceptions import CIWorkflowGenerationError, CIStatusRetrievalError
from app.services.github.github_client import github_client
from app.services.github.exceptions import GitHubIntegrationError

logger = logging.getLogger("devforge.ci.service")


def utcnow():
    return datetime.now(timezone.utc)


class CIWorkflowService:
    """
    Manages GitHub Actions CI workflow generation, status querying,
    and PostgreSQL persistence.
    """

    def generate_ci_workflow(
        self,
        workspace_path: Path,
        template_id: str,
        app_name: str,
        app_port: int = 8000
    ) -> Path:
        """
        Generate .github/workflows/ci.yml in the target workspace.
        """
        try:
            workflow_dir = workspace_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)
            workflow_file = workflow_dir / "ci.yml"

            yaml_content = workflow_generator.generate_workflow_yaml(
                template_id=template_id,
                app_name=app_name,
                port=app_port
            )

            # Validate YAML syntax
            yaml.safe_load(yaml_content)

            workflow_file.write_text(yaml_content, encoding="utf-8")
            logger.info(f"Generated GitHub Actions workflow for '{app_name}' at {workflow_file}")
            return workflow_file
        except Exception as e:
            logger.error(f"Failed to generate CI workflow for {app_name}: {e}")
            raise CIWorkflowGenerationError(f"Failed to generate CI workflow: {e}") from e

    def normalize_ci_status(self, status: Optional[str], conclusion: Optional[str]) -> str:
        """
        Map GitHub Actions run status and conclusion to DevForge standard:
        UNKNOWN, QUEUED, RUNNING, PASSED, FAILED.
        """
        if not status:
            return "UNKNOWN"
        status_clean = status.lower()
        if status_clean == "completed":
            if conclusion and conclusion.lower() == "success":
                return "PASSED"
            return "FAILED"
        elif status_clean in ("in_progress", "waiting", "requested"):
            return "RUNNING"
        elif status_clean == "queued":
            return "QUEUED"
        return "UNKNOWN"

    def get_ci_status(self, app: Application, db: Session) -> Dict[str, Any]:
        """
        Retrieve cached or fresh CI status for the given application.
        """
        return {
            "status": app.ci_status or "UNKNOWN",
            "workflow": app.ci_workflow or "CI",
            "run_id": app.ci_run_id,
            "run_url": app.ci_run_url,
            "last_run_at": app.ci_last_run_at.isoformat() if app.ci_last_run_at else None,
            "application_id": app.id,
            "application_name": app.name
        }

    def refresh_ci_status(self, app: Application, db: Session) -> Dict[str, Any]:
        """
        Query GitHub Actions REST API, update application CI metadata in PostgreSQL,
        and record an activity audit event.
        """
        repo_name = app.repository_name or app.name
        branch = app.repository_default_branch or app.branch or "main"

        try:
            runs = github_client.get_workflow_runs(repo_name=repo_name, branch=branch)
            if runs:
                latest_run = runs[0]
                norm_status = self.normalize_ci_status(
                    status=latest_run.get("status"),
                    conclusion=latest_run.get("conclusion")
                )
                app.ci_status = norm_status
                app.ci_workflow = latest_run.get("name", "CI")
                app.ci_run_id = str(latest_run.get("id")) if latest_run.get("id") else None
                app.ci_run_url = latest_run.get("html_url")
                
                # Parse created_at / updated_at
                run_ts_str = latest_run.get("updated_at") or latest_run.get("created_at")
                if run_ts_str:
                    try:
                        app.ci_last_run_at = datetime.fromisoformat(run_ts_str.replace("Z", "+00:00"))
                    except Exception:
                        app.ci_last_run_at = utcnow()
                else:
                    app.ci_last_run_at = utcnow()
            else:
                # No runs recorded yet on GitHub
                if app.provisioning_status == "READY":
                    app.ci_status = "QUEUED"
                else:
                    app.ci_status = "UNKNOWN"

            db.commit()
            db.refresh(app)

            # Record activity event
            db.add(Activity(
                actor="devforge.ci",
                action=f"CI status refreshed: {app.ci_status}",
                target=f"{app.name} (run #{app.ci_run_id or 'none'})",
                target_type="ci",
                status="completed" if app.ci_status == "PASSED" else "failed" if app.ci_status == "FAILED" else "in_progress",
                details=f"GitHub Actions run status: {app.ci_status} for repository {repo_name}",
                created_at=utcnow()
            ))
            db.commit()

            return self.get_ci_status(app, db)
        except GitHubIntegrationError as ghe:
            logger.warning(f"Could not refresh CI status from GitHub for {app.name}: {ghe}")
            return self.get_ci_status(app, db)
        except Exception as e:
            logger.error(f"Unexpected error refreshing CI status for {app.name}: {e}")
            raise CIStatusRetrievalError(f"Failed to refresh CI status: {e}") from e


workflow_service = CIWorkflowService()
