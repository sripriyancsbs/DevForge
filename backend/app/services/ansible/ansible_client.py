import os
import re
import json
import shutil
import logging
import subprocess
from typing import Tuple, Dict, Any, Optional

from app.services.ansible.exceptions import (
    AnsibleNotInstalledError,
    AnsibleSecurityError,
    AnsiblePlaybookNotFoundError,
)

logger = logging.getLogger("devforge.ansible.client")

ANSI_ESCAPE_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """Strip ANSI / terminal color escape codes from output strings."""
    if not text:
        return ""
    return ANSI_ESCAPE_REGEX.sub("", text)


class AnsibleClient:
    """
    Subprocess-based, sandboxed runner for ansible-playbook.
    Enforces path isolation, timeout limits, and security controls.
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        if workspace_dir:
            self.workspace_dir = os.path.abspath(workspace_dir)
        else:
            # Fallback to /app/ansible in Docker, or relative to project root
            base_app = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
            candidate = os.path.join(base_app, "ansible")
            if os.path.isdir(candidate):
                self.workspace_dir = candidate
            elif os.path.isdir("/app/ansible"):
                self.workspace_dir = "/app/ansible"
            else:
                self.workspace_dir = os.path.abspath("ansible")

    def is_installed(self) -> bool:
        """Check if ansible-playbook executable is available in PATH."""
        return shutil.which("ansible-playbook") is not None

    def get_version(self) -> str:
        """Return the installed Ansible version string."""
        if not self.is_installed():
            raise AnsibleNotInstalledError("ansible-playbook executable is not installed or not in PATH.")
        try:
            res = subprocess.run(
                ["ansible-playbook", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            first_line = res.stdout.strip().split("\n")[0] if res.stdout else "Unknown"
            return strip_ansi(first_line)
        except Exception as e:
            logger.error(f"Error fetching Ansible version: {e}")
            return "Unknown"

    def _resolve_safe_path(self, relative_path: str) -> str:
        """
        Validate and resolve a path within the workspace directory.
        Strictly prevents directory traversal and unauthorized path escapes.
        """
        if not relative_path or not relative_path.strip():
            raise AnsibleSecurityError("Path cannot be empty.")

        clean_rel = relative_path.strip().replace("\\", "/")
        if ".." in clean_rel.split("/") or clean_rel.startswith("/"):
            raise AnsibleSecurityError(f"Directory traversal or absolute paths forbidden: {relative_path}")

        resolved = os.path.abspath(os.path.join(self.workspace_dir, clean_rel))
        if not resolved.startswith(self.workspace_dir):
            raise AnsibleSecurityError(f"Path escape attempted outside Ansible workspace: {relative_path}")

        return resolved

    def run_playbook(
        self,
        playbook_rel_path: str,
        inventory_rel_path: str = "inventories/development/hosts.yml",
        extra_vars: Optional[Dict[str, Any]] = None,
        timeout: int = 120
    ) -> Tuple[int, str, str]:
        """
        Execute an approved playbook within the sandboxed environment.
        Returns: (return_code, stdout, stderr)
        """
        if not self.is_installed():
            raise AnsibleNotInstalledError("ansible-playbook executable is not installed or not in PATH.")

        playbook_path = self._resolve_safe_path(playbook_rel_path)
        if not os.path.isfile(playbook_path):
            raise AnsiblePlaybookNotFoundError(f"Playbook file does not exist: {playbook_rel_path}")

        inventory_path = self._resolve_safe_path(inventory_rel_path)
        if not os.path.isfile(inventory_path):
            raise AnsibleSecurityError(f"Inventory file does not exist: {inventory_rel_path}")

        # Environment configuration
        env = os.environ.copy()
        env["ANSIBLE_FORCE_COLOR"] = "0"
        env["ANSIBLE_NOCOWS"] = "1"
        ansible_cfg = os.path.join(self.workspace_dir, "ansible.cfg")
        if os.path.isfile(ansible_cfg):
            env["ANSIBLE_CONFIG"] = ansible_cfg

        cmd = [
            "ansible-playbook",
            "-i", inventory_path,
            playbook_path
        ]

        if extra_vars:
            # Pass extra vars safely formatted as JSON
            cmd.extend(["-e", json.dumps(extra_vars)])

        logger.info(f"Executing Ansible playbook: {' '.join(cmd[:4])} (cwd: {self.workspace_dir})")

        try:
            process = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False
            )
            clean_stdout = strip_ansi(process.stdout)
            clean_stderr = strip_ansi(process.stderr)
            return process.returncode, clean_stdout, clean_stderr
        except subprocess.TimeoutExpired as te:
            stdout = strip_ansi(te.stdout.decode() if isinstance(te.stdout, bytes) else str(te.stdout or ""))
            stderr = f"Execution timed out after {timeout} seconds."
            logger.error(f"Ansible playbook execution timed out: {playbook_rel_path}")
            return -1, stdout, stderr
        except Exception as e:
            logger.error(f"Unexpected error running Ansible playbook: {e}")
            return -1, "", str(e)


ansible_client = AnsibleClient()
