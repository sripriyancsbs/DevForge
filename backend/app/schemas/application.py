import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_ENVIRONMENTS = {"production", "staging", "development", "preview"}
ALLOWED_TEMPLATES = {"python-fastapi", "react-vite", "go-microservice", "node-service"}
ALLOWED_RUNTIMES = {"python", "node", "go", "react"}
ALLOWED_DATABASES = {"none", "postgresql", "mysql", "redis"}
ALLOWED_STRATEGIES = {"rolling", "recreate", "canary"}

TEMPLATE_DEFAULTS = {
    "python-fastapi": {"runtime": "python", "runtime_display": "Python 3.12 (FastAPI)", "port": 8000},
    "react-vite": {"runtime": "react", "runtime_display": "Node.js 20 (Vite)", "port": 3000},
    "go-microservice": {"runtime": "go", "runtime_display": "Go 1.22", "port": 8080},
    "node-service": {"runtime": "node", "runtime_display": "Node.js 20", "port": 3000},
}


class ApplicationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=64, description="RFC 1123 DNS-compliant application name")
    slug: Optional[str] = Field(None, min_length=2, max_length=80)
    description: Optional[str] = Field(None, max_length=500)
    team: str = Field(default="Platform Engineering", min_length=2, max_length=100)
    runtime: str = Field(default="Python 3.12 (FastAPI)", min_length=2, max_length=100)
    template: Optional[str] = Field(default="python-fastapi", max_length=100)
    repository_url: Optional[str] = Field(None, max_length=255)
    repository_owner: Optional[str] = Field(None, max_length=100)
    repository_name: Optional[str] = Field(None, max_length=100)
    repository_default_branch: Optional[str] = Field(default="main", max_length=100)
    branch: str = Field(default="main", min_length=1, max_length=100)
    environment: str = Field(default="production")
    version: str = Field(default="v1.0.0", min_length=1, max_length=50)
    port: int = Field(default=8000, ge=1, le=65535, description="Network port between 1 and 65535")
    replicas: int = Field(default=2, ge=1, le=50, description="Instance count between 1 and 50")
    database_type: str = Field(default="none", max_length=50)
    deployment_strategy: str = Field(default="rolling", max_length=50)
    provisioning_status: str = Field(default="READY", max_length=30)
    provisioning_error: Optional[str] = None
    generated_path: Optional[str] = None
    manifest_yaml: Optional[str] = None
    ci_status: str = Field(default="UNKNOWN", max_length=30)
    ci_workflow: Optional[str] = Field(default="CI", max_length=100)
    ci_run_id: Optional[str] = None
    ci_run_url: Optional[str] = None
    ci_last_run_at: Optional[datetime] = None
    image_repository: Optional[str] = None
    image_tag: Optional[str] = None
    image_digest: Optional[str] = None
    image_status: Optional[str] = "PENDING"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError(
                "Application name must be lowercase alphanumeric and hyphens, "
                "cannot start or end with a hyphen (RFC 1123 format)."
            )
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Allowed environments: {', '.join(sorted(ALLOWED_ENVIRONMENTS))}"
            )
        return v


class ApplicationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = Field(None, max_length=500)
    team: Optional[str] = Field(default="Platform Engineering", min_length=2, max_length=100)
    runtime: Optional[str] = None
    template: Optional[str] = Field(default="python-fastapi")
    environment: str = Field(default="development")
    database_type: str = Field(default="none")
    deployment_strategy: str = Field(default="rolling")
    repository_url: Optional[str] = None
    branch: str = Field(default="main", min_length=1, max_length=100)
    version: str = Field(default="v1.0.0", min_length=1, max_length=50)
    port: Optional[int] = Field(None, ge=1, le=65535)
    replicas: int = Field(default=2, ge=1, le=50)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", v):
            raise ValueError(
                "Application name must be lowercase alphanumeric and hyphens, "
                "cannot start or end with a hyphen (RFC 1123 format)."
            )
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Application name contains invalid directory traversal characters.")
        return v

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: Optional[str]) -> str:
        if not v:
            return "python-fastapi"
        v = v.strip().lower()
        if v not in ALLOWED_TEMPLATES:
            raise ValueError(
                f"Invalid template '{v}'. Supported templates: {', '.join(sorted(ALLOWED_TEMPLATES))}"
            )
        return v

    @field_validator("runtime")
    @classmethod
    def validate_runtime(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_clean = v.strip().lower()
        # Accept either canonical ('python', 'react') or display ('Python 3.12 (FastAPI)')
        matched = False
        for r in ALLOWED_RUNTIMES:
            if r in v_clean:
                matched = True
                break
        if not matched:
            raise ValueError(
                f"Invalid runtime '{v}'. Supported runtimes: {', '.join(sorted(ALLOWED_RUNTIMES))}"
            )
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Allowed environments: {', '.join(sorted(ALLOWED_ENVIRONMENTS))}"
            )
        return v

    @field_validator("database_type")
    @classmethod
    def validate_database_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_DATABASES:
            raise ValueError(
                f"Invalid database_type '{v}'. Supported options: {', '.join(sorted(ALLOWED_DATABASES))}"
            )
        return v

    @field_validator("deployment_strategy")
    @classmethod
    def validate_deployment_strategy(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_STRATEGIES:
            raise ValueError(
                f"Invalid deployment_strategy '{v}'. Supported options: {', '.join(sorted(ALLOWED_STRATEGIES))}"
            )
        return v


class ApplicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=64)
    description: Optional[str] = Field(None, max_length=500)
    team: Optional[str] = Field(None, min_length=2, max_length=100)
    runtime: Optional[str] = None
    template: Optional[str] = None
    repository_url: Optional[str] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None
    repository_default_branch: Optional[str] = None
    branch: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    replicas: Optional[int] = Field(None, ge=1, le=50)
    database_type: Optional[str] = None
    deployment_strategy: Optional[str] = None
    provisioning_status: Optional[str] = None


class ApplicationResponse(ApplicationBase):
    id: int
    slug: str
    status: str
    last_deployment_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationProvisioningResponse(BaseModel):
    application: ApplicationResponse
    provisioning_status: str
    job_id: Optional[int] = None
    generated_path: Optional[str] = None
    manifest: Optional[str] = None
    files_generated: List[str] = Field(default_factory=list)
    message: str
