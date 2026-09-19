from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_infrastructure_status():
    return {
        "summary": {
            "total_nodes": 18,
            "healthy_nodes": 18,
            "managed_databases": 6,
            "redis_caches": 4,
            "network_gateways": 3,
            "monthly_estimate": "$4,280 / mo"
        },
        "clusters": [
            {
                "name": "prod-useast1-primary",
                "region": "us-east-1",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 8,
                "cpu_utilization": "54%",
                "memory_utilization": "68%",
                "status": "healthy"
            },
            {
                "name": "stage-useast2-secondary",
                "region": "us-east-2",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 4,
                "cpu_utilization": "32%",
                "memory_utilization": "45%",
                "status": "healthy"
            },
            {
                "name": "dev-uswest2-sandbox",
                "region": "us-west-2",
                "provider": "AWS EKS",
                "version": "v1.28.7",
                "nodes": 4,
                "cpu_utilization": "22%",
                "memory_utilization": "30%",
                "status": "healthy"
            },
            {
                "name": "preview-eucentral1",
                "region": "eu-central-1",
                "provider": "AWS EKS",
                "version": "v1.29.3",
                "nodes": 2,
                "cpu_utilization": "15%",
                "memory_utilization": "20%",
                "status": "healthy"
            }
        ],
        "datastores": [
            {
                "name": "postgres-primary-prod",
                "engine": "PostgreSQL 16.2",
                "allocated_storage": "500 GB (34% used)",
                "connections": "48 / 200",
                "status": "healthy"
            },
            {
                "name": "redis-cluster-session",
                "engine": "Redis 7.2",
                "allocated_storage": "16 GB (62% used)",
                "connections": "180 / 1000",
                "status": "healthy"
            },
            {
                "name": "clickhouse-analytics",
                "engine": "ClickHouse 24.1",
                "allocated_storage": "2 TB (45% used)",
                "connections": "12 / 100",
                "status": "healthy"
            }
        ]
    }


# =========================================================================
# Phase 7 — Terraform Infrastructure Endpoints
# =========================================================================

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.terraform_run import TerraformRun
from app.services.terraform.terraform_client import terraform_client
from app.services.terraform.plan_service import plan_service
from app.services.terraform.apply_service import apply_service
from app.services.terraform.exceptions import (
    TerraformError,
    TerraformNotInstalledError,
    TerraformSecurityError,
    TerraformPlanError,
    TerraformApplyError,
)


class TerraformPlanRequest(BaseModel):
    environment: str = Field(default="development", description="Target environment")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Optional variable overrides")


class TerraformApplyRequest(BaseModel):
    environment: str = Field(default="development", description="Target environment")
    run_id: Optional[int] = Field(default=None, description="Optional previous plan run ID to apply")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Optional variable overrides")


@router.get("/terraform")
def get_terraform_status(db: Session = Depends(get_db)):
    """Return current Terraform installation, latest run, and managed resource status."""
    installed = terraform_client.is_installed()
    version = terraform_client.get_version() if installed else None

    # Retrieve the latest run for development
    latest_run = (
        db.query(TerraformRun)
        .order_by(TerraformRun.id.desc())
        .first()
    )

    status_val = latest_run.status if latest_run else ("READY" if installed else "NOT_INSTALLED")
    last_op = f"terraform {latest_run.operation}" if latest_run else None
    resources_count = latest_run.resources_count if (latest_run and latest_run.resources_count > 0) else (3 if status_val == "APPLIED" else 0)

    return {
        "installed": installed,
        "version": version,
        "provider": "Kubernetes (Local)",
        "environment": "development",
        "status": status_val,
        "last_operation": last_op,
        "resources_count": resources_count,
        "latest_run": latest_run.to_dict() if latest_run else None,
    }


@router.post("/terraform/plan")
def plan_terraform(req: TerraformPlanRequest = TerraformPlanRequest(), db: Session = Depends(get_db)):
    """Generate a Terraform plan for the specified environment."""
    try:
        res = plan_service.generate_plan(db, environment=req.environment, var_overrides=req.variables)
        return res
    except TerraformSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TerraformNotInstalledError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (TerraformPlanError, TerraformError) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/terraform/apply")
def apply_terraform(req: TerraformApplyRequest = TerraformApplyRequest(), db: Session = Depends(get_db)):
    """Apply Terraform infrastructure changes for the specified environment."""
    try:
        res = apply_service.apply_infrastructure(
            db,
            environment=req.environment,
            var_overrides=req.variables,
            run_id=req.run_id,
        )
        return res
    except TerraformSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TerraformNotInstalledError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except (TerraformApplyError, TerraformError) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/terraform/runs")
def list_terraform_runs(limit: int = 10, db: Session = Depends(get_db)):
    """List recent Terraform plan/apply runs."""
    runs = db.query(TerraformRun).order_by(TerraformRun.id.desc()).limit(limit).all()
    return [r.to_dict() for r in runs]


@router.get("/terraform/runs/{run_id}")
def get_terraform_run(run_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific Terraform run."""
    run = db.query(TerraformRun).filter(TerraformRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Terraform run #{run_id} not found")
    return run.to_dict()

