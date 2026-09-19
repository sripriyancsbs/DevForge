import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.ansible_execution import AnsibleExecution
from app.models.application import Application
from app.models.activity import Activity
from app.services.ansible.ansible_client import ansible_client
from app.services.ansible.playbook_service import playbook_service
from app.services.ansible.exceptions import (
    AnsibleError,
    AnsibleSecurityError,
    AnsiblePlaybookNotFoundError,
)

logger = logging.getLogger("devforge.ansible.execution")


class ExecutionService:
    """Manages Ansible execution lifecycle, persistence, and worker processing."""

    def _record_activity(
        self,
        db: Session,
        action: str,
        target: str,
        target_type: str = "ansible",
        status: str = "completed",
        details: Optional[str] = None
    ):
        """Helper to emit consistent audit activity records."""
        try:
            act = Activity(
                actor="system",
                action=action,
                target=target,
                target_type=target_type,
                status=status,
                details=details
            )
            db.add(act)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to record Ansible activity event: {e}")
            db.rollback()

    def create_execution(
        self,
        db: Session,
        playbook_name: str,
        application_id: Optional[int] = None,
        environment_id: str = "development"
    ) -> AnsibleExecution:
        """Validate inputs, insert PENDING Ansible execution record, and emit audit event."""
        # 1. Validate playbook name
        playbook_meta = playbook_service.get_playbook(playbook_name)
        playbook_service.resolve_inventory(environment_id)

        # 2. Validate application if provided
        app_name = None
        if application_id is not None:
            app = db.query(Application).filter(Application.id == application_id).first()
            if not app:
                raise AnsibleError(f"Application with ID {application_id} not found.")
            app_name = app.name

        # 3. Create execution record
        execution = AnsibleExecution(
            application_id=application_id,
            environment_id=environment_id,
            playbook_name=playbook_name,
            status="PENDING",
            output=None,
            error_output=None,
            return_code=None,
            started_at=None,
            completed_at=None
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # 4. Log Activity
        target_desc = app_name if app_name else f"env:{environment_id}"
        self._record_activity(
            db=db,
            action="Ansible execution started",
            target=f"{playbook_name} ({target_desc})",
            target_type="ansible",
            status="in_progress",
            details=f"Queued Ansible playbook '{playbook_name}' for execution in environment '{environment_id}'."
        )

        logger.info(f"Queued Ansible execution #{execution.id} for playbook '{playbook_name}'")
        return execution

    def acquire_next_execution(self, db: Session) -> Optional[AnsibleExecution]:
        """
        Acquire the next queued PENDING execution with database row locking.
        Uses SELECT ... FOR UPDATE OF ansible_executions SKIP LOCKED.
        """
        try:
            execution = (
                db.query(AnsibleExecution)
                .filter(AnsibleExecution.status == "PENDING")
                .order_by(AnsibleExecution.created_at.asc())
                .with_for_update(of=AnsibleExecution, skip_locked=True)
                .first()
            )
            return execution
        except Exception as e:
            logger.error(f"Error acquiring next Ansible execution: {e}")
            return None

    def execute_job(self, execution_id: int, db: Session) -> AnsibleExecution:
        """
        Execute an acquired Ansible execution job.
        Transitions: PENDING -> RUNNING -> SUCCESS / FAILED.
        """
        execution = db.query(AnsibleExecution).filter(AnsibleExecution.id == execution_id).first()
        if not execution:
            raise AnsibleError(f"Ansible execution #{execution_id} not found.")

        # Transition to RUNNING
        execution.status = "RUNNING"
        execution.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(execution)

        # Resolve playbook & inventory paths
        try:
            playbook_rel = playbook_service.validate_playbook(execution.playbook_name)
            inventory_rel = playbook_service.resolve_inventory(execution.environment_id)
        except Exception as err:
            execution.status = "FAILED"
            execution.error_output = str(err)
            execution.return_code = 1
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            return execution

        # Build extra variables
        extra_vars: Dict[str, Any] = {
            "app_env": execution.environment_id
        }

        app_name = None
        if execution.application_id:
            app = db.query(Application).filter(Application.id == execution.application_id).first()
            if app:
                app_name = app.name
                extra_vars["app_name"] = app.name
                extra_vars["app_port"] = getattr(app, "port", 8000) or 8000
        elif execution.playbook_name == "configure_application":
            extra_vars["app_name"] = "inventory-api"
            extra_vars["app_port"] = 8000

        logger.info(f"Running Ansible execution #{execution.id} ({execution.playbook_name})...")
        rc, stdout, stderr = ansible_client.run_playbook(
            playbook_rel_path=playbook_rel,
            inventory_rel_path=inventory_rel,
            extra_vars=extra_vars,
            timeout=180
        )

        execution.return_code = rc
        execution.output = stdout
        execution.error_output = stderr if stderr else None
        execution.completed_at = datetime.now(timezone.utc)

        target_desc = app_name if app_name else f"env:{execution.environment_id}"

        if rc == 0:
            execution.status = "SUCCESS"
            self._record_activity(
                db=db,
                action="Ansible playbook completed",
                target=f"{execution.playbook_name} ({target_desc})",
                target_type="ansible",
                status="completed",
                details=f"Playbook '{execution.playbook_name}' completed successfully (rc=0)."
            )
        else:
            execution.status = "FAILED"
            self._record_activity(
                db=db,
                action="Ansible execution failed",
                target=f"{execution.playbook_name} ({target_desc})",
                target_type="ansible",
                status="failed",
                details=f"Playbook '{execution.playbook_name}' failed with return code {rc}."
            )

        try:
            from app.core.metrics import record_ansible_metric
            record_ansible_metric(execution.playbook_name, execution.status, execution.duration_seconds)
        except Exception:
            pass

        db.commit()
        db.refresh(execution)
        logger.info(f"Ansible execution #{execution.id} finished with status: {execution.status} (rc={rc})")
        return execution

    def retry_execution(self, execution_id: int, db: Session) -> AnsibleExecution:
        """Retry a failed or completed execution by re-queuing it as PENDING."""
        execution = db.query(AnsibleExecution).filter(AnsibleExecution.id == execution_id).first()
        if not execution:
            raise AnsibleError(f"Ansible execution #{execution_id} not found.")

        execution.status = "PENDING"
        execution.output = None
        execution.error_output = None
        execution.return_code = None
        execution.started_at = None
        execution.completed_at = None
        db.commit()
        db.refresh(execution)

        target_desc = execution.application.name if execution.application else f"env:{execution.environment_id}"
        self._record_activity(
            db=db,
            action="Ansible execution retried",
            target=f"{execution.playbook_name} ({target_desc})",
            target_type="ansible",
            status="in_progress",
            details=f"Re-queued Ansible execution #{execution.id} for playbook '{execution.playbook_name}'."
        )

        logger.info(f"Ansible execution #{execution.id} re-queued for retry")
        return execution

    def get_execution(self, execution_id: int, db: Session) -> AnsibleExecution:
        """Fetch a single execution by ID."""
        execution = db.query(AnsibleExecution).filter(AnsibleExecution.id == execution_id).first()
        if not execution:
            raise AnsibleError(f"Ansible execution #{execution_id} not found.")
        return execution

    def list_executions(
        self,
        db: Session,
        application_id: Optional[int] = None,
        environment_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[AnsibleExecution]:
        """Query execution history with optional filtering."""
        query = db.query(AnsibleExecution)
        if application_id is not None:
            query = query.filter(AnsibleExecution.application_id == application_id)
        if environment_id:
            query = query.filter(AnsibleExecution.environment_id == environment_id)
        if status:
            query = query.filter(AnsibleExecution.status == status.upper())

        return query.order_by(AnsibleExecution.created_at.desc()).limit(limit).all()


execution_service = ExecutionService()
