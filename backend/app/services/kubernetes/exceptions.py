class KubernetesError(Exception):
    """Base exception for all Kubernetes related operations."""
    pass

class KubernetesClusterUnavailableError(KubernetesError):
    """Raised when Kubernetes cluster cannot be reached."""
    pass

class KubernetesAuthError(KubernetesError):
    """Raised when authentication to Kubernetes fails."""
    pass

class KubernetesNamespaceError(KubernetesError):
    """Raised when namespace operations fail or namespace is missing."""
    pass

class KubernetesManifestError(KubernetesError):
    """Raised when generating or parsing Kubernetes YAML manifest fails."""
    pass

class KubernetesDeploymentError(KubernetesError):
    """Raised when Deployment resource cannot be created or updated."""
    pass

class KubernetesServiceError(KubernetesError):
    """Raised when Service resource cannot be created or updated."""
    pass

class KubernetesRolloutTimeoutError(KubernetesError):
    """Raised when deployment rollout verification exceeds configured timeout."""
    pass

class KubernetesImagePullError(KubernetesError):
    """Raised when pods cannot pull the specified container image (ErrImagePull / ImagePullBackOff)."""
    pass

class KubernetesRolloutFailedError(KubernetesError):
    """Raised when rollout fails due to pod crashes or failure conditions."""
    pass
