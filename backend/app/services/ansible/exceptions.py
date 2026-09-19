class AnsibleError(Exception):
    """Base exception for all Ansible-related operations."""
    pass


class AnsibleNotInstalledError(AnsibleError):
    """Raised when ansible or ansible-playbook executable is not found."""
    pass


class AnsibleSecurityError(AnsibleError):
    """Raised when a security policy violation or forbidden parameter is detected."""
    pass


class AnsiblePlaybookNotFoundError(AnsibleError):
    """Raised when a requested playbook is not recognized or not found in allowlist."""
    pass


class AnsibleExecutionError(AnsibleError):
    """Raised when playbook execution fails with a non-zero exit code or error."""
    pass
