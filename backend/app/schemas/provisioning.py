from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.application import ApplicationResponse

class ProvisioningJobResponse(BaseModel):
    id: int
    application_id: int
    status: str
    template: str
    current_step: str
    attempt: int
    max_attempts: int
    is_retryable: bool
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreationAsyncResponse(BaseModel):
    application: ApplicationResponse
    job_id: int
    status: str
    message: str
