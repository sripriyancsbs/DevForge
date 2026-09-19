"""
Custom exception hierarchy for Argo CD and GitOps operations.
"""

class ArgoCDError(Exception):
    """Base exception for all Argo CD operations."""
    pass

class ArgoCDUnavailableError(ArgoCDError):
    """Raised when the Argo CD server or Kubernetes CRD is unreachable."""
    pass

class ArgoCDAuthenticationError(ArgoCDError):
    """Raised when authentication to Argo CD or Git repository fails."""
    pass

class ArgoCDApplicationNotFoundError(ArgoCDError):
    """Raised when an Argo CD Application custom resource does not exist."""
    pass

class ArgoCDSyncError(ArgoCDError):
    """Raised when an Argo CD sync or reconciliation operation fails."""
    pass

class GitOpsManifestError(ArgoCDError):
    """Raised when Kustomize manifest generation or validation fails."""
    pass
