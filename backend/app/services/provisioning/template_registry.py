import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.template import Template

logger = logging.getLogger("devforge.provisioning.template_registry")

# RFC 1123 DNS-compliant name format
RFC_1123_REGEX = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

# Forbidden characters in variables to prevent command / template injection
INJECTION_CHARS = {";", "&", "|", "`", "$", "\n", "\r", "\t"}

# Aliases for backward compatibility
TEMPLATE_ALIASES = {
    "node-service": "node-express",
    "go-microservice": "go-gin",
}

CANONICAL_TEMPLATES = {
    "python-fastapi": {
        "name": "Python FastAPI API",
        "description": "High-performance asynchronous REST microservice with automatic OpenAPI schema, Pydantic validation, and health probe endpoints.",
        "runtime": "python",
        "framework": "FastAPI",
        "version": "1.0.0",
        "default_port": 8000,
        "supported_environments": ["development", "staging", "production"],
        "generated_project_structure": [
            "main.py",
            "requirements.txt",
            "Dockerfile",
            ".dockerignore",
            "README.md",
            "devforge.yaml",
            ".github/workflows/ci.yml",
            "tests/test_main.py"
        ],
        "required_variables": ["application_name", "environment", "port"],
        "optional_variables": {
            "description": "string",
            "team": "string",
            "database_type": "string",
            "replicas": "number"
        },
        "default_values": {
            "port": 8000,
            "replicas": 2,
            "database_type": "postgresql",
            "deployment_strategy": "rolling"
        },
        "validation_rules": {
            "name_pattern": "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
            "port_range": [1, 65535]
        },
        "is_enabled": True
    },
    "node-express": {
        "name": "Node.js Express API",
        "description": "Event-driven Node.js REST API service built with Express, structured routing, test suite, and optimized containerfile.",
        "runtime": "node",
        "framework": "Express",
        "version": "1.0.0",
        "default_port": 3000,
        "supported_environments": ["development", "staging", "production"],
        "generated_project_structure": [
            "server.js",
            "package.json",
            "Dockerfile",
            ".dockerignore",
            "README.md",
            "devforge.yaml",
            ".github/workflows/ci.yml",
            "test.js"
        ],
        "required_variables": ["application_name", "environment", "port"],
        "optional_variables": {
            "description": "string",
            "team": "string",
            "database_type": "string",
            "replicas": "number"
        },
        "default_values": {
            "port": 3000,
            "replicas": 2,
            "database_type": "none",
            "deployment_strategy": "rolling"
        },
        "validation_rules": {
            "name_pattern": "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
            "port_range": [1, 65535]
        },
        "is_enabled": True
    },
    "go-gin": {
        "name": "Go Gin API",
        "description": "Compiled, low-latency microservice powered by the Gin Gonic web framework with multi-stage minimal container build.",
        "runtime": "go",
        "framework": "Gin",
        "version": "1.0.0",
        "default_port": 8080,
        "supported_environments": ["development", "staging", "production"],
        "generated_project_structure": [
            "main.go",
            "go.mod",
            "Dockerfile",
            ".dockerignore",
            "README.md",
            "devforge.yaml",
            ".github/workflows/ci.yml",
            "main_test.go"
        ],
        "required_variables": ["application_name", "environment", "port"],
        "optional_variables": {
            "description": "string",
            "team": "string",
            "database_type": "string",
            "replicas": "number"
        },
        "default_values": {
            "port": 8080,
            "replicas": 2,
            "database_type": "none",
            "deployment_strategy": "rolling"
        },
        "validation_rules": {
            "name_pattern": "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
            "port_range": [1, 65535]
        },
        "is_enabled": True
    },
    "react-vite": {
        "name": "React + Vite Frontend",
        "description": "Client-side SPA with TypeScript, Tailwind CSS, and optimized production container build.",
        "runtime": "react",
        "framework": "React",
        "version": "1.0.0",
        "default_port": 3000,
        "supported_environments": ["development", "staging", "production"],
        "generated_project_structure": [
            "package.json",
            "index.html",
            "Dockerfile",
            ".dockerignore",
            "README.md",
            "devforge.yaml",
            ".github/workflows/ci.yml"
        ],
        "required_variables": ["application_name", "environment", "port"],
        "optional_variables": {
            "description": "string",
            "team": "string",
            "database_type": "string",
            "replicas": "number"
        },
        "default_values": {
            "port": 3000,
            "replicas": 2,
            "database_type": "none",
            "deployment_strategy": "rolling"
        },
        "validation_rules": {
            "name_pattern": "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
            "port_range": [1, 65535]
        },
        "is_enabled": True
    }
}


def get_templates_root() -> Path:
    """Resolve the directory containing starter templates safely."""
    env_dir = os.getenv("DEVFORGE_TEMPLATES_DIR")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir).resolve()

    candidates = [
        Path("/app/templates"),
        Path(__file__).resolve().parent.parent.parent.parent.parent / "templates",
        Path(__file__).resolve().parent.parent.parent.parent / "templates",
        Path.cwd() / "templates",
        Path.cwd().parent / "templates",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()

    fallback = (Path.cwd() / "templates").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


class TemplateRegistry:
    def __init__(self, templates_root: Optional[Path] = None):
        self.templates_root = templates_root or get_templates_root()

    def resolve_template_id(self, template_id: str) -> str:
        """Resolve aliases and normalize template identifier."""
        if not template_id:
            return "python-fastapi"
        cleaned = template_id.strip().lower()
        return TEMPLATE_ALIASES.get(cleaned, cleaned)

    def get_template_dir(self, template_id: str) -> Path:
        """
        Get safe filesystem directory for template with path traversal protection.
        """
        canonical_id = self.resolve_template_id(template_id)
        base = self.templates_root.resolve()

        # Reject path traversal tokens
        if ".." in template_id or "/" in template_id or "\\" in template_id:
            raise ValueError(f"Invalid template identifier '{template_id}': path traversal characters are forbidden.")

        target = (base / canonical_id).resolve()
        if not target.is_relative_to(base):
            raise ValueError(f"Path traversal detected: '{template_id}' resolves outside templates directory.")

        if not target.exists() or not target.is_dir():
            # Check if alias folder exists on disk (e.g. node-service or go-microservice)
            alt = (base / template_id).resolve()
            if alt.exists() and alt.is_dir() and alt.is_relative_to(base):
                return alt
            raise FileNotFoundError(f"Template directory '{canonical_id}' not found on disk at {target}")

        return target

    def list_templates(self, db: Optional[Session] = None, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all available templates from PostgreSQL (or canonical fallback).
        """
        if db:
            query = db.query(Template)
            if enabled_only:
                query = query.filter(Template.is_enabled == True)
            db_templates = query.order_by(Template.template_id.asc(), Template.version.desc()).all()
            if db_templates:
                return [t.to_dict() for t in db_templates]

        # Fallback to canonical list
        results = []
        for tid, meta in CANONICAL_TEMPLATES.items():
            if enabled_only and not meta.get("is_enabled", True):
                continue
            tpl_copy = dict(meta)
            tpl_copy["id"] = tid
            tpl_copy["template_id"] = tid
            results.append(tpl_copy)
        return results

    def get_template_metadata(self, template_id: str, version: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific template and version.
        """
        canonical_id = self.resolve_template_id(template_id)
        target_version = version or "1.0.0"

        if db:
            db_tpl = (
                db.query(Template)
                .filter(Template.template_id == canonical_id)
                .filter(Template.version == target_version)
                .first()
            )
            if db_tpl:
                if not db_tpl.is_enabled:
                    raise ValueError(f"Template '{template_id}' version '{target_version}' is disabled.")
                return db_tpl.to_dict()

        if canonical_id in CANONICAL_TEMPLATES:
            meta = CANONICAL_TEMPLATES[canonical_id]
            if not meta.get("is_enabled", True):
                raise ValueError(f"Template '{template_id}' is disabled.")
            if version and meta.get("version") != target_version:
                raise ValueError(f"Template '{template_id}' version '{target_version}' not found.")
            res = dict(meta)
            res["id"] = canonical_id
            res["template_id"] = canonical_id
            return res

        raise ValueError(
            f"Unsupported template '{template_id}'. "
            f"Allowed templates: {', '.join(sorted(CANONICAL_TEMPLATES.keys()))}"
        )

    def validate_variables(self, template_id: str, version: Optional[str], variables: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Validate variables against template specifications, checking types, lengths,
        RFC 1123 naming, path traversal, and injection characters.
        """
        meta = self.get_template_metadata(template_id, version, db)

        app_name = variables.get("application_name") or variables.get("name")
        if not app_name:
            raise ValueError("Variable 'application_name' is required.")

        app_name = str(app_name).strip().lower()
        if ".." in app_name or "/" in app_name or "\\" in app_name:
            raise ValueError("Application name contains invalid directory traversal characters.")

        for char in INJECTION_CHARS:
            if char in app_name:
                raise ValueError(f"Application name contains forbidden character: {repr(char)}")

        if len(app_name) < 2 or len(app_name) > 64:
            raise ValueError(f"Application name '{app_name}' length must be between 2 and 64 characters.")

        if not RFC_1123_REGEX.match(app_name):
            raise ValueError(
                f"Application name '{app_name}' must be lowercase alphanumeric and hyphens, "
                "cannot start or end with a hyphen (RFC 1123 format)."
            )

        for char in INJECTION_CHARS:
            if char in app_name:
                raise ValueError(f"Application name contains forbidden character: {repr(char)}")

        # Validate Port
        port = variables.get("port")
        if port is not None:
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    raise ValueError(f"Port {port_num} must be between 1 and 65535.")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid container port: {port}") from e

        # Validate Environment
        env = variables.get("environment")
        if env:
            supported = meta.get("supported_environments", ["development", "staging", "production"])
            if env not in supported and env not in {"development", "staging", "production", "preview"}:
                raise ValueError(f"Environment '{env}' not supported. Allowed: {', '.join(supported)}")

        # Sanitize any string variables against shell injection
        for k, v in variables.items():
            if isinstance(v, str):
                for char in INJECTION_CHARS:
                    if char in v and k not in {"description"}:
                        raise ValueError(f"Variable '{k}' contains forbidden character: {repr(char)}")

        return {
            "valid": True,
            "template_id": meta["template_id"],
            "version": meta["version"],
            "application_name": app_name,
            "port": int(port) if port is not None else meta.get("default_port", 8000),
            "environment": env or "development",
            "runtime": meta["runtime"],
            "framework": meta["framework"]
        }

    def preview_project(
        self,
        template_id: str,
        version: Optional[str],
        variables: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate a lightweight preview of the project structure and primary manifest
        without writing anything to disk.
        """
        validated = self.validate_variables(template_id, version, variables, db)
        meta = self.get_template_metadata(template_id, version, db)
        app_name = validated["application_name"]
        env = validated["environment"]
        port = validated["port"]

        expected_files = meta.get("generated_project_structure", [])

        manifest_preview = f"""apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: "{app_name}"
  version: "{meta.get('version', '1.0.0')}"
  description: "{variables.get('description') or f'DevForge application {app_name}'}"
  team: "{variables.get('team') or 'Platform Engineering'}"
spec:
  runtime: "{meta['runtime']}"
  template: "{meta['template_id']}"
  framework: "{meta['framework']}"
  environment: "{env}"
  port: {port}
  database:
    type: "{variables.get('database_type', 'none')}"
  build:
    docker: true
    dockerfile: "Dockerfile"
  deployment:
    strategy: "{variables.get('deployment_strategy', 'rolling')}"
    replicas: {variables.get('replicas', 2)}
  healthCheck:
    path: "/healthz"
    port: {port}"""

        return {
            "template_id": meta["template_id"],
            "template_name": meta["name"],
            "template_version": meta["version"],
            "runtime": meta["runtime"],
            "framework": meta["framework"],
            "application_name": app_name,
            "environment": env,
            "files": expected_files,
            "manifest_preview": manifest_preview,
            "key_generated_components": [
                f"Main application entrypoint and {meta['framework']} routing",
                "Standard health check probe endpoint (/healthz)",
                "Optimized multi-stage container build (Dockerfile, .dockerignore)",
                "Automated GitHub Actions CI pipeline (.github/workflows/ci.yml)",
                "Standard DevForge application manifest (devforge.yaml)",
                "Unit and integration test suite verification"
            ]
        }


template_registry = TemplateRegistry()
