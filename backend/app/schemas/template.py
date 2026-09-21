from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TemplateResponse(BaseModel):
    id: Optional[int] = None
    template_id: str
    name: str
    description: Optional[str] = None
    runtime: str
    framework: str
    version: str = "1.0.0"
    supported_environments: List[str] = ["development", "staging", "production"]
    generated_project_structure: List[str] = []
    required_variables: List[str] = ["application_name", "environment", "port"]
    optional_variables: Dict[str, Any] = {}
    default_values: Dict[str, Any] = {}
    validation_rules: Dict[str, Any] = {}
    is_enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TemplateValidateRequest(BaseModel):
    application_name: str
    environment: Optional[str] = "development"
    port: Optional[int] = 8000
    description: Optional[str] = None
    team: Optional[str] = "Platform Engineering"
    database_type: Optional[str] = "none"
    deployment_strategy: Optional[str] = "rolling"
    replicas: Optional[int] = 2
    version: Optional[str] = "1.0.0"

class TemplateValidateResponse(BaseModel):
    valid: bool
    template_id: str
    version: str
    application_name: str
    port: int
    environment: str
    runtime: str
    framework: str

class TemplatePreviewRequest(BaseModel):
    application_name: str
    environment: Optional[str] = "development"
    port: Optional[int] = 8000
    description: Optional[str] = None
    team: Optional[str] = "Platform Engineering"
    database_type: Optional[str] = "none"
    deployment_strategy: Optional[str] = "rolling"
    replicas: Optional[int] = 2
    version: Optional[str] = "1.0.0"

class TemplatePreviewResponse(BaseModel):
    template_id: str
    template_name: str
    template_version: str
    runtime: str
    framework: str
    application_name: str
    environment: str
    files: List[str]
    manifest_preview: str
    key_generated_components: List[str] = []

class TemplateCreateRequest(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    runtime: str
    framework: str
    version: str = "1.0.0"
    supported_environments: List[str] = ["development", "staging", "production"]
    generated_project_structure: List[str] = []
    required_variables: List[str] = ["application_name", "environment", "port"]
    optional_variables: Dict[str, Any] = {}
    default_values: Dict[str, Any] = {}
    validation_rules: Dict[str, Any] = {}
    is_enabled: bool = True

class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
