class TerraformError(Exception):
    """Base exception for all Terraform operations."""
    pass


class TerraformNotInstalledError(TerraformError):
    """Raised when the terraform CLI binary is not found on the host or container."""
    pass


class TerraformSecurityError(TerraformError):
    """Raised when an illegal path or forbidden command execution attempt is detected."""
    pass


class TerraformInitError(TerraformError):
    """Raised when terraform init fails."""
    pass


class TerraformValidateError(TerraformError):
    """Raised when terraform validate fails."""
    pass


class TerraformPlanError(TerraformError):
    """Raised when terraform plan fails."""
    pass


class TerraformApplyError(TerraformError):
    """Raised when terraform apply fails."""
    pass
