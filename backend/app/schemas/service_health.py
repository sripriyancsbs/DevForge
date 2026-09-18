from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ServiceHealthResponse(BaseModel):
    id: int
    service_name: str
    status: str
    cpu_percent: float
    memory_mb: str
    requests_per_sec: int
    error_rate: str
    uptime: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ActivityResponse(BaseModel):
    id: int
    actor: str
    action: str
    target: str
    target_type: str
    status: str
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
