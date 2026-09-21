import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

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
        application_id: Optional[int] = None,
        name: Optional[str] = None,
        template: Optional[str] = None,
        runtime: Optional[str] = None,
        environment: str = "development",
        port: int = 8000,
        version: str = "1.0.0",
        description: Optional[str] = None,
        team: str = "Platform Engineering",
        database_type: str = "none",
        deployment_strategy: str = "rolling",
        replicas: int = 2,
        target_dir: Optional[Union[str, Path]] = None,
        template_id: Optional[str] = None,
        application_name: Optional[str] = None
    ) -> ProjectGenerationResult:
        """
        Idempotently scaffold a real, complete application project from a starter template.
        """
        eff_template = template_id or template or "python-fastapi"
        eff_name = application_name or name or "sample-app"
        eff_app_id = application_id or 1
        eff_port = port or 8000
        eff_env = environment or "development"
        eff_version = version or "1.0.0"
        eff_desc = description or f"{eff_name} API application"
        eff_team = team or "Platform Engineering"
        eff_db = database_type or "none"
        eff_replicas = replicas or 2

        if target_dir is not None:
            resolved_target = Path(target_dir).resolve()
            resolved_target.mkdir(parents=True, exist_ok=True)
        else:
            resolved_target = self.prepare_workspace(eff_app_id)

        # Validate template exists and is complete
        template_service.validate_template(eff_template)
        template_dir = template_service.get_template_dir(eff_template)

        # Infer runtime if omitted
        eff_runtime = runtime
        if not eff_runtime:
            tpl_lower = eff_template.lower()
            if "python" in tpl_lower or "fastapi" in tpl_lower:
                eff_runtime = "python"
            elif "node" in tpl_lower or "express" in tpl_lower:
                eff_runtime = "nodejs"
            elif "go" in tpl_lower or "gin" in tpl_lower:
                eff_runtime = "go"
            elif "react" in tpl_lower or "vite" in tpl_lower:
                eff_runtime = "node"
            else:
                eff_runtime = "python"

        try:
            created_files: List[str] = []

            # Rendering context with both lowercase and uppercase variations
            context: Dict[str, str] = {
                "application_name": eff_name,
                "app_name": eff_name,
                "name": eff_name,
                "description": eff_desc,
                "port": str(eff_port),
                "environment": eff_env,
                "version": eff_version,
                "team": eff_team,
                "database_type": eff_db,
                "deployment_strategy": deployment_strategy or "rolling",
                "runtime": eff_runtime,
                "template_id": eff_template,
                "replicas": str(eff_replicas),
            }
            # Add uppercase keys (e.g. PORT, APP_NAME, RUNTIME)
            for k, v in list(context.items()):
                context[k.upper()] = str(v)

            # Copy and render template files
            for root, dirs, files in os.walk(template_dir):
                # Filter out unwanted directories
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".pytest_cache"}]
                rel_root = Path(root).relative_to(template_dir)
                dest_dir = resolved_target / rel_root
                dest_dir.mkdir(parents=True, exist_ok=True)

                for f in files:
                    if f in {".DS_Store", "Thumbs.db"}:
                        continue
                    src_file = Path(root) / f
                    dest_file = dest_dir / f
                    rel_file_path = str((rel_root / f).as_posix())

                    is_text = (
                        src_file.suffix.lower() in TEXT_EXTENSIONS
                        or f in {"Dockerfile", "devforge.yaml", ".dockerignore", ".env.example", "Makefile"}
                    )

                    if is_text:
                        try:
                            content = src_file.read_text(encoding="utf-8")
                            for var_name, val in context.items():
                                # Replace {{var}} and {{ var }}
                                content = re.sub(r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}", str(val), content)
                            dest_file.write_text(content, encoding="utf-8")
                        except UnicodeDecodeError:
                            shutil.copy2(src_file, dest_file)
                    else:
                        shutil.copy2(src_file, dest_file)

                    created_files.append(rel_file_path)

            # Ensure devforge.yaml exists
            manifest_file = resolved_target / "devforge.yaml"
            if not manifest_file.exists():
                manifest_yaml = manifest_service.generate_manifest(
                    app_name=eff_name,
                    runtime=eff_runtime,
                    port=eff_port,
                    template=eff_template,
                    database_type=eff_db,
                    environment=eff_env,
                    deployment_strategy=deployment_strategy,
                    replicas=eff_replicas
                )
                manifest_file.write_text(manifest_yaml, encoding="utf-8")
                created_files.append("devforge.yaml")
            else:
                manifest_yaml = manifest_file.read_text(encoding="utf-8")

            # Ensure standard CI workflow exists
            workflow_path = resolved_target / ".github" / "workflows" / "ci.yml"
            if not workflow_path.exists():
                workflow_path.parent.mkdir(parents=True, exist_ok=True)
                from app.services.ci.workflow_generator import workflow_generator
                ci_content = workflow_generator.generate_workflow(
                    app_name=eff_name,
                    runtime=eff_runtime,
                    template=eff_template
                )
                workflow_path.write_text(ci_content, encoding="utf-8")
                created_files.append(".github/workflows/ci.yml")

            return ProjectGenerationResult(
                application_id=eff_app_id,
                app_name=eff_name,
                project_dir=resolved_target,
                relative_path=f"app_{eff_app_id}" if target_dir is None else str(resolved_target),
                manifest_yaml=manifest_yaml,
                files_generated=sorted(list(set(created_files)))
            )

        except Exception as e:
            raise RuntimeError(f"Failed to generate project for application '{eff_name}' (id: {eff_app_id}): {str(e)}") from e

    def validate_generated_project(
        self,
        application_id: Optional[int] = None,
        template: Optional[str] = None,
        project_dir: Optional[Union[str, Path]] = None,
        application_name: Optional[str] = None,
        template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify that all required files exist in the generated workspace, devforge.yaml is valid, and no unresolved tokens remain."""
        eff_template = template_id or template or "python-fastapi"
        if project_dir is not None:
            target_dir = Path(project_dir).resolve()
        else:
            eff_app_id = application_id or 1
            target_dir = self.get_isolated_workspace(eff_app_id)

        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Generated workspace does not exist: {target_dir}")

        # Check template required files
        req_files = ["devforge.yaml", "Dockerfile"]
        clean_tpl = (eff_template or "").strip().lower()
        if clean_tpl == "python-fastapi":
            req_files.extend(["main.py", "requirements.txt"])
        elif clean_tpl in {"node-express", "node-service"}:
            req_files.extend(["server.js", "package.json"])
        elif clean_tpl in {"go-gin", "go-microservice"}:
            req_files.extend(["main.go", "go.mod"])
        elif clean_tpl == "react-vite":
            req_files.extend(["package.json", "index.html"])

        for rf in req_files:
            target_f = target_dir / rf
            if not target_f.exists():
                raise FileNotFoundError(f"Generated project missing required file: {rf}")
            if target_f.is_file() and target_f.stat().st_size == 0:
                raise ValueError(f"Generated file '{rf}' is unexpectedly empty.")

        # Validate manifest content if file exists
        manifest_file = target_dir / "devforge.yaml"
        if manifest_file.exists():
            manifest_content = manifest_file.read_text(encoding="utf-8")
            manifest_service.validate_manifest(manifest_content)

        # Validate CI workflow exists and is non-empty if present
        ci_file = target_dir / ".github" / "workflows" / "ci.yml"
        if ci_file.exists():
            if not ci_file.read_text(encoding="utf-8").strip():
                raise ValueError("Generated CI workflow .github/workflows/ci.yml is empty.")

        # Check that NO unresolved template tokens remain in text files
        token_pattern = re.compile(r"\{\{[A-Za-z0-9_]+\}\}")
        for path in target_dir.rglob("*"):
            if path.is_file() and (path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"Dockerfile", "devforge.yaml"}):
                try:
                    text_content = path.read_text(encoding="utf-8", errors="ignore")
                    matches = token_pattern.findall(text_content)
                    if matches:
                        rel = path.relative_to(target_dir)
                        raise ValueError(f"Unresolved template variables {matches} detected in generated file '{rel}'")
                except UnicodeDecodeError:
                    pass

        return {"valid": True, "target_dir": str(target_dir), "template": eff_template}


project_generator = ProjectGenerator()
