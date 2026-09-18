from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError

class ManifestMetadata(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    version: str = Field(default="1.0.0")
    description: Optional[str] = None
    team: str = Field(default="Platform Engineering")

class DatabaseSpec(BaseModel):
    type: str = Field(default="none")

class BuildSpec(BaseModel):
    docker: bool = Field(default=True)
    dockerfile: str = Field(default="Dockerfile")

class DeploymentSpec(BaseModel):
    strategy: str = Field(default="rolling")
    replicas: int = Field(default=2, ge=1, le=50)

class HealthCheckSpec(BaseModel):
    path: str = Field(default="/healthz")
    port: int = Field(default=8000, ge=1, le=65535)

class ManifestSpec(BaseModel):
    runtime: str
    template: str
    environment: str = Field(default="development")
    port: int = Field(default=8000, ge=1, le=65535)
    database: DatabaseSpec = Field(default_factory=DatabaseSpec)
    build: BuildSpec = Field(default_factory=BuildSpec)
    deployment: DeploymentSpec = Field(default_factory=DeploymentSpec)
    healthCheck: HealthCheckSpec = Field(default_factory=HealthCheckSpec)

class DevForgeManifest(BaseModel):
    apiVersion: str = Field(default="devforge/v1")
    kind: str = Field(default="ApplicationManifest")
    metadata: ManifestMetadata
    spec: ManifestSpec


class ManifestService:
    def generate_manifest(
        self,
        name: str,
        template: str,
        runtime: str,
        environment: str = "development",
        port: int = 8000,
        version: str = "1.0.0",
        description: Optional[str] = None,
        team: str = "Platform Engineering",
        database_type: str = "none",
        deployment_strategy: str = "rolling",
        replicas: int = 2
    ) -> str:
        """Generate a valid devforge.yaml string conforming to apiVersion: devforge/v1."""
        # Determine default health path
        health_path = "/healthz"
        if template == "go-microservice":
            health_path = "/health"
        elif template == "react-vite":
            health_path = "/"

        manifest_obj = DevForgeManifest(
            apiVersion="devforge/v1",
            kind="ApplicationManifest",
            metadata=ManifestMetadata(
                name=name,
                version=version,
                description=description or f"DevForge self-serviced application: {name}",
                team=team
            ),
            spec=ManifestSpec(
                runtime=runtime,
                template=template,
                environment=environment,
                port=port,
                database=DatabaseSpec(type=database_type),
                build=BuildSpec(docker=True, dockerfile="Dockerfile"),
                deployment=DeploymentSpec(strategy=deployment_strategy, replicas=replicas),
                healthCheck=HealthCheckSpec(path=health_path, port=port)
            )
        )

        manifest_dict = manifest_obj.model_dump()
        return yaml.dump(manifest_dict, sort_keys=False, indent=2)

    def validate_manifest(self, yaml_content: str) -> Dict[str, Any]:
        """Parse and validate a devforge.yaml content string."""
        try:
            data = yaml.safe_load(yaml_content)
        except Exception as e:
            raise ValueError(f"Invalid YAML syntax in devforge.yaml: {str(e)}")

        if not isinstance(data, dict):
            raise ValueError("devforge.yaml must contain a top-level mapping/dictionary")

        if data.get("apiVersion") != "devforge/v1":
            raise ValueError(f"Unsupported apiVersion '{data.get('apiVersion')}'. Expected 'devforge/v1'")

        try:
            validated = DevForgeManifest(**data)
            return validated.model_dump()
        except ValidationError as ve:
            raise ValueError(f"devforge.yaml schema validation failed: {ve}")


manifest_service = ManifestService()
