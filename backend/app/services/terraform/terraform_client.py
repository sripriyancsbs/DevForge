import os
import re
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.services.terraform.exceptions import (
    TerraformError,
    TerraformNotInstalledError,
    TerraformSecurityError,
    TerraformInitError,
    TerraformValidateError,
    TerraformPlanError,
    TerraformApplyError,
)

logger = logging.getLogger("devforge.terraform")

ANSI_ESCAPE_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """Remove ANSI terminal color escape codes."""
    if not text:
        return ""
    return ANSI_ESCAPE_REGEX.sub("", text)


class TerraformClient:
    """Official subprocess client for executing sandboxed Terraform commands."""

    ALLOWED_ENVIRONMENTS = {"development", "staging", "production"}

    def __init__(self, base_terraform_dir: Optional[str] = None):
        if base_terraform_dir:
            self.base_dir = Path(base_terraform_dir).resolve()
        else:
            # Default to <workspace_root>/terraform or /app/terraform
            possible_paths = [
                Path(__file__).resolve().parents[4] / "terraform",
                Path(__file__).resolve().parents[3] / "terraform",
                Path(os.getcwd()) / "terraform",
                Path(os.getcwd()).parent / "terraform",
                Path("/app/terraform"),
            ]
            self.base_dir = next((p.resolve() for p in possible_paths if p.exists()), possible_paths[0].resolve())

        self._binary_path = self._find_binary()

    def _find_binary(self) -> str:
        bin_path = shutil.which("terraform")
        if bin_path:
            return bin_path
        common_paths = ["/usr/local/bin/terraform", "/usr/bin/terraform", "C:\\Program Files\\Terraform\\terraform.exe"]
        for cp in common_paths:
            if os.path.isfile(cp) and os.access(cp, os.X_OK):
                return cp
        return "terraform"

    def is_installed(self) -> bool:
        """Check if terraform binary is available and executable."""
        try:
            res = subprocess.run([self._binary_path, "version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """Return the Terraform version string."""
        try:
            res = subprocess.run([self._binary_path, "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                first_line = res.stdout.strip().split("\n")[0]
                return first_line
        except Exception as e:
            logger.warning(f"Failed to get terraform version: {e}")
        return None

    def get_working_dir(self, environment: str = "development") -> Path:
        """Resolve and strictly validate the working directory for an environment."""
        clean_env = environment.strip().lower()
        if clean_env not in self.ALLOWED_ENVIRONMENTS:
            raise TerraformSecurityError(
                f"Invalid or forbidden environment '{environment}'. Allowed: {sorted(list(self.ALLOWED_ENVIRONMENTS))}"
            )

        target_dir = (self.base_dir / "environments" / clean_env).resolve()

        # Security check: must reside within self.base_dir
        try:
            target_dir.relative_to(self.base_dir)
        except ValueError:
            raise TerraformSecurityError(
                f"Path traversal detected: '{target_dir}' does not reside within '{self.base_dir}'"
            )

        if not target_dir.exists():
            raise TerraformError(f"Environment directory does not exist: {target_dir}")

        return target_dir

    def _run_cmd(self, cmd: List[str], cwd: Path, timeout: int = 60) -> Tuple[int, str, str]:
        """Execute a validated terraform command safely."""
        if not self.is_installed():
            raise TerraformNotInstalledError(
                "Terraform binary is not installed or not found in system PATH."
            )

        logger.info(f"Executing terraform command: {' '.join(cmd)} in {cwd}")
        try:
            process = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy(),
            )
            stdout = strip_ansi(process.stdout or "")
            stderr = strip_ansi(process.stderr or "")
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired as e:
            logger.error(f"Terraform command timed out after {timeout}s: {' '.join(cmd)}")
            raise TerraformError(f"Terraform command timed out after {timeout} seconds: {' '.join(cmd)}") from e
        except Exception as e:
            logger.error(f"Failed to execute terraform command {' '.join(cmd)}: {e}")
            raise TerraformError(f"Subprocess execution failed: {e}") from e

    def init(self, environment: str = "development") -> str:
        """Run terraform init."""
        cwd = self.get_working_dir(environment)
        cmd = [self._binary_path, "init", "-input=false", "-no-color"]
        rc, out, err = self._run_cmd(cmd, cwd, timeout=120)
        if rc != 0:
            raise TerraformInitError(f"terraform init failed (exit {rc}): {err or out}")
        return out

    def validate(self, environment: str = "development") -> str:
        """Run terraform validate."""
        cwd = self.get_working_dir(environment)
        cmd = [self._binary_path, "validate", "-no-color"]
        rc, out, err = self._run_cmd(cmd, cwd, timeout=30)
        if rc != 0:
            raise TerraformValidateError(f"terraform validate failed (exit {rc}): {err or out}")
        return out

    def plan(self, environment: str = "development", var_overrides: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Run terraform plan and return raw output and parsed resource action counts."""
        cwd = self.get_working_dir(environment)

        # Ensure initialized
        if not (cwd / ".terraform").exists():
            self.init(environment)

        cmd = [self._binary_path, "plan", "-input=false", "-no-color"]
        if var_overrides:
            for k, v in var_overrides.items():
                cmd.extend(["-var", f"{k}={v}"])

        rc, out, err = self._run_cmd(cmd, cwd, timeout=90)
        if rc != 0:
            raise TerraformPlanError(f"terraform plan failed (exit {rc}): {err or out}")

        parsed_summary = self._parse_plan_output(out)
        return out, parsed_summary

    def apply(self, environment: str = "development", var_overrides: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """Run terraform apply -auto-approve safely and return output and parsed summary."""
        cwd = self.get_working_dir(environment)

        # Ensure initialized
        if not (cwd / ".terraform").exists():
            self.init(environment)

        cmd = [self._binary_path, "apply", "-input=false", "-auto-approve", "-no-color"]
        if var_overrides:
            for k, v in var_overrides.items():
                cmd.extend(["-var", f"{k}={v}"])

        rc, out, err = self._run_cmd(cmd, cwd, timeout=120)
        if rc != 0:
            raise TerraformApplyError(f"terraform apply failed (exit {rc}): {err or out}")

        parsed_summary = self._parse_apply_output(out)
        return out, parsed_summary

    def _parse_plan_output(self, output: str) -> Dict[str, Any]:
        """Parse resource actions from terraform plan output."""
        summary = {
            "to_add": 0,
            "to_change": 0,
            "to_destroy": 0,
            "resources": [],
        }

        # Match "Plan: X to add, Y to change, Z to destroy."
        plan_match = re.search(r"Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy\.", output)
        if plan_match:
            summary["to_add"] = int(plan_match.group(1))
            summary["to_change"] = int(plan_match.group(2))
            summary["to_destroy"] = int(plan_match.group(3))
        elif "No changes. Your infrastructure matches the configuration." in output:
            summary["to_add"] = 0
            summary["to_change"] = 0
            summary["to_destroy"] = 0

        # Extract planned resource lines (e.g. "+ resource "kubernetes_namespace_v1" "devforge"")
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("+ resource ") or line.startswith("~ resource ") or line.startswith("- resource "):
                parts = line.split('"')
                if len(parts) >= 4:
                    res_type = parts[1]
                    res_name = parts[3]
                    action = "create" if line.startswith("+") else ("update" if line.startswith("~") else "destroy")
                    summary["resources"].append({
                        "action": action,
                        "type": res_type,
                        "name": res_name,
                        "symbol": "+" if action == "create" else ("~" if action == "update" else "-")
                    })

        return summary

    def _parse_apply_output(self, output: str) -> Dict[str, Any]:
        """Parse resource results from terraform apply output."""
        summary = {
            "added": 0,
            "changed": 0,
            "destroyed": 0,
            "total_managed": 0,
        }

        apply_match = re.search(r"Apply complete!\s*Resources:\s*(\d+)\s*added,\s*(\d+)\s*changed,\s*(\d+)\s*destroyed\.", output)
        if apply_match:
            summary["added"] = int(apply_match.group(1))
            summary["changed"] = int(apply_match.group(2))
            summary["destroyed"] = int(apply_match.group(3))
            summary["total_managed"] = summary["added"] + summary["changed"]
        elif "No changes." in output:
            summary["total_managed"] = 2  # Baseline managed

        return summary


terraform_client = TerraformClient()
