import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.services.provisioning.template_service import template_service
from app.services.provisioning.manifest_service import manifest_service

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".mod", ".go", ".html", ".css", ".md", ".txt", ".env", ".toml", ".sh"
}

@dataclass
class ProjectGenerationResult:
    application_id: int
    app_name: str
    project_dir: Path
    relative_path: str
    manifest_yaml: str
    files_generated: List[str]


def get_workspace_root() -> Path:
    """Resolve the root workspace directory for generated applications."""
    env_workspace = os.getenv("DEVFORGE_WORKSPACE_DIR")
    if env_workspace:
        base = Path(env_workspace).resolve()
    else:
        # Check standard root
        candidates = [
            Path("/app/.devforge/generated"),
            Path(__file__).resolve().parent.parent.parent.parent.parent / ".devforge" / "generated",
            Path.cwd() / ".devforge" / "generated",
        ]
        chosen = None
        for c in candidates:
            try:
                c.mkdir(parents=True, exist_ok=True)
                chosen = c.resolve()
                break
            except Exception:
                continue
        base = chosen or (Path.cwd() / ".devforge" / "generated").resolve()

    base.mkdir(parents=True, exist_ok=True)
    return base


class ProjectGenerator:
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or get_workspace_root()

    def get_isolated_workspace(self, application_id: int) -> Path:
        """
        Derive an isolated workspace directory using the application_id.
        Prevents filesystem path injection from application names.
        Example: .devforge/generated/app_123/
        """
        if not application_id or not isinstance(application_id, int) or application_id <= 0:
            raise ValueError(f"Valid positive integer application_id required, got {application_id}")

        base = self.workspace_root.resolve()
        folder_name = f"app_{application_id}"
        target = (base / folder_name).resolve()

        if not target.is_relative_to(base):
            raise ValueError(f"Path traversal detected: '{folder_name}' resolves outside workspace root.")

        return target

    def get_workspace_path(self, application_id: int) -> Path:
        """Alias for get_isolated_workspace."""
        return self.get_isolated_workspace(application_id)

    def prepare_workspace(self, application_id: int) -> Path:
        """
        Idempotent workspace preparation.
        If directory already exists, ensures it is ready for safe generation.
        """
        target_dir = self.get_isolated_workspace(application_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def generate_project(
        self,
        application_id: int,
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
    ) -> ProjectGenerationResult:
        """
        Idempotently scaffold a real, complete application project from a starter template
        inside the isolated directory .devforge/generated/app_{application_id}/.
        """
        target_dir = self.prepare_workspace(application_id)

        # Validate template exists and is complete
        template_service.validate_template(template)
        template_dir = template_service.get_template_dir(template)

        # Generate standardized devforge.yaml manifest
        manifest_yaml = manifest_service.generate_manifest(
            name=name,
            template=template,
            runtime=runtime,
            environment=environment,
            port=port,
            version=version,
            description=description,
            team=team,
            database_type=database_type,
            deployment_strategy=deployment_strategy,
            replicas=replicas
        )

        tokens: Dict[str, str] = {
            "{{APPLICATION_NAME}}": name,
            "{{PORT}}": str(port),
            "{{ENVIRONMENT}}": environment,
            "{{DATABASE_TYPE}}": database_type,
            "{{DEPLOYMENT_STRATEGY}}": deployment_strategy,
            "{{REPLICAS}}": str(replicas),
            "{{VERSION}}": version,
            "{{DESCRIPTION}}": description or f"DevForge application {name}",
            "{{TEAM}}": team,
            "{{RUNTIME}}": runtime,
        }

        created_files: List[str] = []

        try:
            # Copy template files recursively with token substitution (idempotent overwrite)
            for src_path in template_dir.rglob("*"):
                rel_path = src_path.relative_to(template_dir)
                dest_path = target_dir / rel_path

                if src_path.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                elif src_path.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    if rel_path.name == "devforge.yaml":
                        dest_path.write_text(manifest_yaml, encoding="utf-8")
                    elif src_path.suffix.lower() in TEXT_EXTENSIONS or src_path.name in {"Dockerfile", ".dockerignore", "requirements.txt"}:
                        content = src_path.read_text(encoding="utf-8", errors="replace")
                        for token, replacement in tokens.items():
                            content = content.replace(token, replacement)
                        dest_path.write_text(content, encoding="utf-8")
                    else:
                        shutil.copy2(src_path, dest_path)

                    created_files.append(str(rel_path).replace("\\", "/"))

            # Ensure devforge.yaml exists
            manifest_file = target_dir / "devforge.yaml"
            if not manifest_file.exists():
                manifest_file.write_text(manifest_yaml, encoding="utf-8")
                created_files.append("devforge.yaml")

            rel_workspace_path = f".devforge/generated/app_{application_id}"

            return ProjectGenerationResult(
                application_id=application_id,
                app_name=name,
                project_dir=target_dir,
                relative_path=rel_workspace_path,
                manifest_yaml=manifest_yaml,
                files_generated=sorted(created_files)
            )

        except Exception as e:
            raise RuntimeError(f"Failed to generate project for application '{name}' (id: {application_id}): {str(e)}") from e

    def validate_generated_project(self, application_id: int, template: str) -> bool:
        """Verify that all required files exist in the generated workspace and devforge.yaml is valid."""
        target_dir = self.get_isolated_workspace(application_id)
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Generated workspace does not exist: {target_dir}")

        # Check template required files
        meta = template_service.list_templates()
        tpl_meta = next((t for t in meta if t["id"] == template), None)
        req_files = ["devforge.yaml", "Dockerfile"]
        if template == "python-fastapi":
            req_files.extend(["main.py", "requirements.txt"])
        elif template == "react-vite":
            req_files.extend(["package.json", "index.html"])
        elif template == "go-microservice":
            req_files.extend(["main.go", "go.mod"])
        elif template == "node-service":
            req_files.extend(["server.js", "package.json"])

        for rf in req_files:
            if not (target_dir / rf).exists():
                raise FileNotFoundError(f"Generated project missing required file: {rf}")

        # Validate manifest content
        manifest_file = target_dir / "devforge.yaml"
        manifest_content = manifest_file.read_text(encoding="utf-8")
        manifest_service.validate_manifest(manifest_content)

        # Phase 4: Validate CI workflow exists and is non-empty
        ci_file = target_dir / ".github" / "workflows" / "ci.yml"
        if not ci_file.exists():
            raise FileNotFoundError("Generated project missing required CI workflow: .github/workflows/ci.yml")
        if not ci_file.read_text(encoding="utf-8").strip():
            raise ValueError("Generated CI workflow .github/workflows/ci.yml is empty.")

        return True


project_generator = ProjectGenerator()
