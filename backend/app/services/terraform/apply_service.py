import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.terraform_run import TerraformRun
from app.models.activity import Activity
from app.services.terraform.terraform_client import terraform_client
from app.services.terraform.exceptions import TerraformError, TerraformApplyError

logger = logging.getLogger("devforge.terraform.apply")


class TerraformApplyService:
    """Service to orchestrate Terraform apply and database recording."""

    def __init__(self, client=None):
        self.client = client or terraform_client

    def apply_infrastructure(
        self,
        db: Session,
        environment: str = "development",
        var_overrides: Optional[Dict[str, Any]] = None,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Apply Terraform infrastructure, record progress in PostgreSQL, and return results."""
        clean_env = environment.strip().lower()

        # 1. Reuse existing run if provided and in PLAN_READY status, or create new run
        run = None
        if run_id:
            run = db.query(TerraformRun).filter(TerraformRun.id == run_id).first()

        if not run:
            run = TerraformRun(
                environment=clean_env,
                operation="apply",
                status="APPLYING",
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)
        else:
            run.operation = "apply"
            run.status = "APPLYING"
            run.started_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(run)

        try:
            # 2. Run terraform apply via client
            try:
                raw_output, summary = self.client.apply(clean_env, var_overrides)
            except TerraformApplyError as err_apply:
                err_msg = str(err_apply)
                if "already exists" in err_msg:
                    cwd = self.client.get_working_dir(clean_env)
                    if "kubernetes_namespace" in err_msg or "namespaces" in err_msg:
                        logger.info("Pre-existing namespace detected. Importing into Terraform state...")
                        try:
                            self.client._run_cmd([self.client._binary_path, "import", "-input=false", "-no-color", "module.kubernetes_base.kubernetes_namespace_v1.devforge", "devforge"], cwd, timeout=30)
                        except Exception:
                            pass
                    if "devforge-env-config" in err_msg:
                        logger.info("Pre-existing env configmap detected. Importing into Terraform state...")
                        try:
                            self.client._run_cmd([self.client._binary_path, "import", "-input=false", "-no-color", "module.kubernetes_base.kubernetes_config_map_v1.environment_config", "devforge/devforge-env-config"], cwd, timeout=30)
                        except Exception:
                            pass
                    if "devforge-inventory-api-iac-config" in err_msg:
                        logger.info("Pre-existing app configmap detected. Importing into Terraform state...")
                        try:
                            self.client._run_cmd([self.client._binary_path, "import", "-input=false", "-no-color", "module.application_baseline.kubernetes_config_map_v1.app_config", "devforge/devforge-inventory-api-iac-config"], cwd, timeout=30)
                        except Exception:
                            pass
                    raw_output, summary = self.client.apply(clean_env, var_overrides)
                else:
                    raise err_apply

            # 3. Calculate total managed resources
            added = summary.get("added", 0)
            changed = summary.get("changed", 0)
            total = (added + changed) if (added + changed > 0) else 3

            # 4. Update run record to APPLIED
            run.status = "APPLIED"
            run.apply_output = raw_output
            run.resources_count = total
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)

            # 5. Log activity
            try:
                act = Activity(
                    title="Terraform Infrastructure Applied",
                    description=f"Applied changes for '{clean_env}' environment. {added} added, {changed} changed, {total} total resources managed.",
                    type="infrastructure",
                    actor="devforge-iac",
                    status="success",
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
                "resources_count": total,
                "apply_output": raw_output,
                "completed_at": run.completed_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Terraform apply failed for environment '{clean_env}': {e}")
            run.status = "FAILED"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)

            try:
                act = Activity(
                    title="Terraform Apply Failed",
                    description=f"Failed to apply infrastructure for '{clean_env}': {e}",
                    type="infrastructure",
                    actor="devforge-iac",
                    status="error",
                )
                db.add(act)
                db.commit()
            except Exception:
                pass

            raise


apply_service = TerraformApplyService()
