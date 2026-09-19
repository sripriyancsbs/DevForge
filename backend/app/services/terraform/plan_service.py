import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.terraform_run import TerraformRun
from app.models.activity import Activity
from app.services.terraform.terraform_client import terraform_client
from app.services.terraform.exceptions import TerraformError

logger = logging.getLogger("devforge.terraform.plan")


class TerraformPlanService:
    """Service to orchestrate Terraform planning and database recording."""

    def __init__(self, client=None):
        self.client = client or terraform_client

    def generate_plan(
        self,
        db: Session,
        environment: str = "development",
        var_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a Terraform plan, record progress in PostgreSQL, and return parsed results."""
        clean_env = environment.strip().lower()

        # 1. Create run record in PLANNING state
        run = TerraformRun(
            environment=clean_env,
            operation="plan",
            status="PLANNING",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            # 2. Run terraform plan via client
            raw_output, summary = self.client.plan(clean_env, var_overrides)

            # 3. Update run record to PLAN_READY
            run.status = "PLAN_READY"
            run.plan_output = raw_output
            run.resources_count = summary.get("to_add", 0) + summary.get("to_change", 0)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)

            # 4. Log activity
            try:
                act = Activity(
                    title="Terraform Plan Generated",
                    description=f"Planned {summary.get('to_add', 0)} resources to add, {summary.get('to_change', 0)} to change for '{clean_env}' environment.",
                    type="infrastructure",
                    actor="devforge-iac",
                    status="info",
                )
                db.add(act)
                db.commit()
            except Exception as act_err:
                logger.warning(f"Failed to record activity: {act_err}")

            return {
                "run_id": run.id,
                "environment": clean_env,
                "status": run.status,
                "summary": summary,
                "plan_output": raw_output,
                "created_at": run.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Terraform plan failed for environment '{clean_env}': {e}")
            run.status = "FAILED"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)

            try:
                act = Activity(
                    title="Terraform Plan Failed",
                    description=f"Failed to plan infrastructure for '{clean_env}': {e}",
                    type="infrastructure",
                    actor="devforge-iac",
                    status="error",
                )
                db.add(act)
                db.commit()
            except Exception:
                pass

            raise


plan_service = TerraformPlanService()
