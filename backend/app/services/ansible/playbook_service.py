from typing import List, Dict, Any
from app.services.ansible.exceptions import AnsiblePlaybookNotFoundError, AnsibleSecurityError

# Strict allowlist of approved playbooks
APPROVED_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "configure_application": {
        "name": "configure_application",
        "title": "Configure Application",
        "description": "Deploys idempotent application directories, logs path, and .env configuration templates.",
        "file": "playbooks/configure_application.yml",
        "scope": "application",
        "required_params": ["app_name"],
        "optional_params": ["app_env", "app_port"],
    },
    "configure_environment": {
        "name": "configure_environment",
        "title": "Configure Environment Baseline",
        "description": "Establishes idempotent environment directory topologies, shared configs, and descriptor markers.",
        "file": "playbooks/configure_environment.yml",
        "scope": "environment",
        "required_params": [],
        "optional_params": ["app_env"],
    },
    "health_check": {
        "name": "health_check",
        "title": "Health Check & Verification",
        "description": "Verifies local filesystem readiness, environment baselines, and application configuration state.",
        "file": "playbooks/health_check.yml",
        "scope": "all",
        "required_params": [],
        "optional_params": ["app_name", "app_env"],
    },
}

SUPPORTED_ENVIRONMENTS = ["development", "staging", "production"]


class PlaybookService:
    """Service to discover, validate, and parameterize approved Ansible playbooks."""

    def list_playbooks(self) -> List[Dict[str, Any]]:
        """Return the list of approved playbooks with metadata."""
        return list(APPROVED_PLAYBOOKS.values())

    def get_playbook(self, playbook_name: str) -> Dict[str, Any]:
        """Fetch metadata for a single approved playbook."""
        clean_name = playbook_name.strip() if playbook_name else ""
        if clean_name not in APPROVED_PLAYBOOKS:
            raise AnsiblePlaybookNotFoundError(
                f"Playbook '{playbook_name}' is not an approved playbook. "
                f"Allowed playbooks: {', '.join(APPROVED_PLAYBOOKS.keys())}"
            )
        return APPROVED_PLAYBOOKS[clean_name]

    def validate_playbook(self, playbook_name: str) -> str:
        """Validate playbook name against allowlist and return its relative path."""
        meta = self.get_playbook(playbook_name)
        return meta["file"]

    def resolve_inventory(self, environment_id: str) -> str:
        """Resolve inventory file path for the requested environment."""
        clean_env = (environment_id or "development").strip().lower()
        if clean_env not in SUPPORTED_ENVIRONMENTS:
            raise AnsibleSecurityError(
                f"Unsupported environment '{environment_id}'. "
                f"Supported environments: {', '.join(SUPPORTED_ENVIRONMENTS)}"
            )
        # Development maps to local hosts.yml; future environments can be added here
        return "inventories/development/hosts.yml"


playbook_service = PlaybookService()
