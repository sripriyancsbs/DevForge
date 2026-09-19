class CIWorkflowError(Exception):
    """Base exception for all CI/CD workflow operations."""
    pass


class CIWorkflowGenerationError(CIWorkflowError):
    """Raised when generating a CI workflow fails."""
    pass


class CIStatusRetrievalError(CIWorkflowError):
    """Raised when retrieving CI status from GitHub Actions fails."""
    pass
