from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CIStatusResponse(BaseModel):
    status: str = Field(..., description="CI status: UNKNOWN, QUEUED, RUNNING, PASSED, FAILED")
    workflow: Optional[str] = Field(default="CI", description="Workflow name")
    run_id: Optional[str] = Field(None, description="GitHub Actions run ID")
    run_url: Optional[str] = Field(None, description="Direct URL to GitHub Actions run")
    last_run_at: Optional[datetime] = Field(None, description="Timestamp of the last CI run")
    application_id: int
    application_name: str
