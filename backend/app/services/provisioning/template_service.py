import os
from pathlib import Path
from typing import Dict, List, Optional

# Supported canonical templates and runtimes
SUPPORTED_TEMPLATES = {
    "python-fastapi": {
        "name": "Python FastAPI",
        "runtime": "python",
        "runtime_display": "Python 3.12 (FastAPI)",
        "default_port": 8000,
        "required_files": ["Dockerfile", "devforge.yaml", "main.py", "requirements.txt"]
    },
    "node-express": {
        "name": "Node.js Express API",
        "runtime": "node",
        "runtime_display": "Node.js 20 (Express)",
        "default_port": 3000,
        "required_files": ["Dockerfile", "devforge.yaml", "server.js", "package.json"]
    },
    "go-gin": {
        "name": "Go Gin API",
        "runtime": "go",
        "runtime_display": "Go 1.22 (Gin)",
        "default_port": 8080,
        "required_files": ["Dockerfile", "devforge.yaml", "main.go", "go.mod"]
    },
    "react-vite": {
        "name": "React + Vite",
        "runtime": "react",
        "runtime_display": "Node.js 20 (Vite)",
        "default_port": 3000,
        "required_files": ["Dockerfile", "devforge.yaml", "package.json", "index.html"]
    },
    "go-microservice": {
        "name": "Go Microservice",
        "runtime": "go",
        "runtime_display": "Go 1.22",
        "default_port": 8080,
        "required_files": ["Dockerfile", "devforge.yaml", "main.go", "go.mod"]
    },
    "node-service": {
        "name": "Node.js API",
        "runtime": "node",
        "runtime_display": "Node.js 20",
        "default_port": 3000,
        "required_files": ["Dockerfile", "devforge.yaml", "server.js", "package.json"]
    }
}

SUPPORTED_RUNTIMES = {"python", "node", "go", "react"}


def get_templates_root() -> Path:
    """Resolve the directory containing starter templates."""
    env_dir = os.getenv("DEVFORGE_TEMPLATES_DIR")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir).resolve()
    
    # Check standard relative paths
    candidates = [
        Path("/app/templates"),  # Inside docker if mounted or copied
        Path(__file__).resolve().parent.parent.parent.parent.parent / "templates", # c:\Agen\DevForge\templates
        Path(__file__).resolve().parent.parent.parent.parent / "templates",
        Path.cwd() / "templates",
        Path.cwd().parent / "templates",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()
    
    # Fallback to local templates folder
    return Path.cwd() / "templates"


class TemplateService:
    def __init__(self, templates_root: Optional[Path] = None):
        self.templates_root = templates_root or get_templates_root()

    def list_templates(self) -> List[Dict]:
        """List all supported starter templates with current availability status."""
        results = []
        for tpl_id, meta in SUPPORTED_TEMPLATES.items():
            tpl_dir = self.templates_root / tpl_id
            is_available = tpl_dir.exists() and tpl_dir.is_dir()
            results.append({
                "id": tpl_id,
                "name": meta["name"],
                "runtime": meta["runtime"],
                "runtime_display": meta["runtime_display"],
                "default_port": meta["default_port"],
                "available": is_available,
                "path": str(tpl_dir) if is_available else None
            })
        return results

    def get_template_dir(self, template_id: str) -> Path:
        """Get the directory of a validated template."""
        if template_id not in SUPPORTED_TEMPLATES:
            raise ValueError(
                f"Unsupported template '{template_id}'. "
                f"Allowed templates: {', '.join(sorted(SUPPORTED_TEMPLATES.keys()))}"
            )
        tpl_dir = (self.templates_root / template_id).resolve()
        if not tpl_dir.exists() or not tpl_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found on disk: {tpl_dir}")
        return tpl_dir

    def validate_template(self, template_id: str) -> bool:
        """Validate template files integrity."""
        tpl_dir = self.get_template_dir(template_id)
        meta = SUPPORTED_TEMPLATES[template_id]
        for req_file in meta.get("required_files", []):
            req_path = tpl_dir / req_file
            if not req_path.exists():
                raise ValueError(f"Template '{template_id}' is missing required file: {req_file}")
        return True

    def validate_runtime_and_template(self, runtime: str, template: str) -> None:
        """Validate that the given runtime and template are compatible."""
        norm_runtime = runtime.strip().lower()
        # Handle prefixes e.g. "python:3.12" or "Python 3.12 (FastAPI)"
        matched_runtime = None
        for r in SUPPORTED_RUNTIMES:
            if r in norm_runtime:
                matched_runtime = r
                break
        
        if not matched_runtime and norm_runtime not in SUPPORTED_RUNTIMES:
            raise ValueError(
                f"Unsupported runtime '{runtime}'. "
                f"Allowed runtimes: {', '.join(sorted(SUPPORTED_RUNTIMES))}"
            )

        if template not in SUPPORTED_TEMPLATES:
            raise ValueError(
                f"Unsupported template '{template}'. "
                f"Allowed templates: {', '.join(sorted(SUPPORTED_TEMPLATES.keys()))}"
            )

        expected_runtime = SUPPORTED_TEMPLATES[template]["runtime"]
        if matched_runtime and matched_runtime != expected_runtime:
            raise ValueError(
                f"Template '{template}' requires runtime '{expected_runtime}', "
                f"but got '{runtime}'"
            )


template_service = TemplateService()
