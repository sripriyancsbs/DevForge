import os
import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.models.application import Application
from app.services.kubernetes.manifest_generator import ManifestGenerator, TEMPLATE_METADATA, sanitize_k8s_name
from app.services.argocd.exceptions import GitOpsManifestError

logger = logging.getLogger("devforge.services.argocd.manifest")

class GitOpsManifestService:
    """
    Generates and maintains GitOps Kustomize application manifest topologies:
    gitops/applications/<app-name>/
      ├── base/
      │   ├── deployment.yaml
      │   ├── service.yaml
      │   └── kustomization.yaml
      └── overlays/
          └── development/
              ├── kustomization.yaml
              └── patch.yaml
    """

    def __init__(self, gitops_root: Optional[str] = None):
        self.gitops_root = Path(gitops_root or os.getenv("DEVFORGE_GITOPS_DIR", "/app/gitops"))
        self.manifest_gen = ManifestGenerator()

    def get_application_gitops_dir(self, app_slug: str) -> Path:
        """Returns root path for an application's GitOps manifests."""
        return self.gitops_root / "applications" / sanitize_k8s_name(app_slug)

    def generate_manifests(
        self,
        application: Application,
        environment: str = "development",
        image_tag: Optional[str] = None,
        replicas: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate full Kustomize manifest tree for an application.
        Returns a dictionary mapping relative file paths to YAML content.
        """
        app_name = sanitize_k8s_name(application.name or application.slug)
        namespace = application.environment if application.environment != "production" else "devforge"
        if environment:
            namespace = "devforge"  # standard devforge runtime namespace

        # Resolve image
        image_repo = application.image_repository or f"ghcr.io/sripriyancsbs/{app_name}"
        tag = image_tag or application.image_tag or "latest"
        full_image = f"{image_repo}:{tag}"

        # Resolve port and probe path
        port = self.manifest_gen.resolve_port(application.template, application.port)
        health_path = self.manifest_gen.resolve_health_path(application.template)
        rep_count = replicas if replicas is not None else (application.replicas or 2)

        # 1. Base Deployment
        deployment_doc = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"devforge-{app_name}",
                "labels": {
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/instance": app_name,
                    "app.kubernetes.io/part-of": "devforge",
                    "app.kubernetes.io/managed-by": "argocd",
                }
            },
            "spec": {
                "replicas": rep_count,
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": app_name,
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app.kubernetes.io/name": app_name,
                            "app.kubernetes.io/instance": app_name,
                            "app.kubernetes.io/part-of": "devforge",
                            "app.kubernetes.io/managed-by": "argocd",
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": app_name,
                                "image": full_image,
                                "imagePullPolicy": "IfNotPresent",
                                "ports": [
                                    {
                                        "name": "http",
                                        "containerPort": port,
                                        "protocol": "TCP",
                                    }
                                ],
                                "env": [
                                    {"name": "ENVIRONMENT", "value": environment},
                                    {"name": "PORT", "value": str(port)},
                                    {"name": "DEVFORGE_APP_NAME", "value": application.name},
                                ],
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "128Mi"},
                                    "limits": {"cpu": "500m", "memory": "512Mi"},
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": health_path, "port": port},
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 3,
                                    "failureThreshold": 3,
                                },
                                "livenessProbe": {
                                    "httpGet": {"path": health_path, "port": port},
                                    "initialDelaySeconds": 10,
                                    "periodSeconds": 15,
                                    "timeoutSeconds": 3,
                                    "failureThreshold": 3,
                                },
                            }
                        ]
                    }
                }
            }
        }

        # 2. Base Service
        service_doc = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"devforge-{app_name}-svc",
                "labels": {
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/instance": app_name,
                    "app.kubernetes.io/part-of": "devforge",
                    "app.kubernetes.io/managed-by": "argocd",
                }
            },
            "spec": {
                "type": "ClusterIP",
                "selector": {
                    "app.kubernetes.io/name": app_name,
                },
                "ports": [
                    {
                        "name": "http",
                        "port": port,
                        "targetPort": port,
                        "protocol": "TCP",
                    }
                ]
            }
        }

        # 3. Base Kustomization
        base_kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": [
                "deployment.yaml",
                "service.yaml"
            ]
        }

        # 4. Overlay Patch
        patch_doc = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"devforge-{app_name}",
            },
            "spec": {
                "replicas": rep_count,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": app_name,
                                "env": [
                                    {"name": "LOG_LEVEL", "value": "DEBUG" if environment == "development" else "INFO"}
                                ]
                            }
                        ]
                    }
                }
            }
        }

        # 5. Overlay Kustomization
        overlay_kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "namespace": namespace,
            "resources": [
                "../../base"
            ],
            "patches": [
                {"path": "patch.yaml"}
            ]
        }

        return {
            "base/deployment.yaml": yaml.dump(deployment_doc, sort_keys=False),
            "base/service.yaml": yaml.dump(service_doc, sort_keys=False),
            "base/kustomization.yaml": yaml.dump(base_kustomization, sort_keys=False),
            f"overlays/{environment}/patch.yaml": yaml.dump(patch_doc, sort_keys=False),
            f"overlays/{environment}/kustomization.yaml": yaml.dump(overlay_kustomization, sort_keys=False),
        }

    def write_manifests_to_disk(
        self,
        application: Application,
        environment: str = "development",
        image_tag: Optional[str] = None,
        replicas: Optional[int] = None
    ) -> Path:
        """
        Generate and persist Kustomize manifests to filesystem.
        Returns the overlay directory path suitable for Argo CD target path.
        """
        app_slug = application.slug or application.name
        app_dir = self.get_application_gitops_dir(app_slug)
        manifests = self.generate_manifests(application, environment, image_tag, replicas)

        for rel_path, content in manifests.items():
            dest = app_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        logger.info(f"Wrote GitOps Kustomize manifests for '{application.name}' to {app_dir}")
        return app_dir / f"overlays/{environment}"

gitops_manifest_service = GitOpsManifestService()
