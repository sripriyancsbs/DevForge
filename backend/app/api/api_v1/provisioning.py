from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.provisioning_job import ProvisioningJob
from app.schemas.provisioning import ProvisioningJobResponse
from app.services.provisioning.service import provisioning_service

router = APIRouter()

@router.get("/{job_id}", response_model=ProvisioningJobResponse)
def get_provisioning_status(job_id: int, db: Session = Depends(get_db)):
    """Fetch real-time provisioning job status and progress step for polling."""
    job = db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provisioning job #{job_id} not found."
        )
    return job


@router.post("/{job_id}/retry", response_model=ProvisioningJobResponse)
def retry_provisioning_job(job_id: int, db: Session = Depends(get_db)):
    """Retry a failed provisioning job."""
    job = db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provisioning job #{job_id} not found."
        )
    if job.status not in ["FAILED", "RETRY"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job #{job_id} is in status '{job.status}' and cannot be retried."
        )

    retried_job = provisioning_service.retry_job(job_id, db)
    return retried_job


@router.get("/by-app/{application_id}", response_model=ProvisioningJobResponse)
def get_latest_job_for_application(application_id: int, db: Session = Depends(get_db)):
    """Fetch the latest provisioning job for a given application ID."""
    job = (
        db.query(ProvisioningJob)
        .filter(ProvisioningJob.application_id == application_id)
        .order_by(ProvisioningJob.created_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No provisioning job found for application #{application_id}."
        )
    return job
