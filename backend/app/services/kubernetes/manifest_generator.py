import re
from typing import Dict, Any, Optional, List
import yaml

from app.services.kubernetes.exceptions import KubernetesManifestError

# Default ports and health probe paths per template
TEMPLATE_METADATA = {
    "python-fastapi": {
        "port": 8000,
        "health_path": "/healthz",
        "probe_initial_delay": 5,
        "probe_period": 10,
    },
    "node-express": {
        "port": 3000,
        "health_path": "/healthz",
        "probe_initial_delay": 5,
        "probe_period": 10,
    },
    "node-service": {
        "port": 3000,
        "health_path": "/healthz",
        "probe_initial_delay": 5,
        "probe_period": 10,
    },
    "go-gin": {
        "port": 8080,
        "health_path": "/healthz",
        "probe_initial_delay": 3,
        "probe_period": 10,
    },
    "go-microservice": {
        "port": 8080,
        "health_path": "/healthz",
        "probe_initial_delay": 3,
        "probe_period": 10,
    },
    "react-vite": {
        "port": 3000,
        "health_path": "/",
        "probe_initial_delay": 5,
        "probe_period": 10,
    },
}


def sanitize_k8s_name(name: str) -> str:
    """
    Sanitize an application or resource name to conform to RFC 1123 DNS subdomain format:
    - lowercase alphanumeric characters or '-'
    - must start and end with an alphanumeric character
    - maximum 63 characters
    """
    if not name:
        return "app"
    clean = re.sub(r"[^a-z0-9\-]", "-", name.lower())
    clean = re.sub(r"-+", "-", clean).strip("-")
    if not clean:
        clean = "app"
    return clean[:63]


class ManifestGenerator:
    """
    Generates Kubernetes manifests (Deployment, Service, ConfigMap)
    in valid Kubernetes YAML format.
    """

    def resolve_port(self, template: Optional[str], configured_port: Optional[int]) -> int:
        """Determine application port from configuration or template default."""
        if configured_port and 1 <= configured_port <= 65535:
            return configured_port
        if template and template in TEMPLATE_METADATA:
            return TEMPLATE_METADATA[template]["port"]
        return 8000

    def resolve_health_path(self, template: Optional[str]) -> str:
        """Determine health probe path based on template."""
        if template and template in TEMPLATE_METADATA:
            return TEMPLATE_METADATA[template]["health_path"]
        return "/healthz"

    def generate_deployment_dict(
        self,
        application_name: str,
        image: str,
        replicas: int = 1,
        port: int = 8000,
        template: Optional[str] = None,
        namespace: str = "devforge",
        environment: str = "development",
        image_pull_secret: Optional[str] = "devforge-ghcr-secret",
        config_map_name: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate Deployment specification dictionary."""
        sanitized_name = sanitize_k8s_name(application_name)
        deployment_name = f"devforge-{sanitized_name}"
        health_path = self.resolve_health_path(template)
        meta = TEMPLATE_METADATA.get(template or "", {})
        init_delay = meta.get("probe_initial_delay", 5)
        period = meta.get("probe_period", 10)

        labels = {
            "app.kubernetes.io/name": sanitized_name,
            "app.kubernetes.io/instance": deployment_name,
            "app.kubernetes.io/part-of": "devforge",
            "app.kubernetes.io/managed-by": "devforge",
            "devforge.io/environment": environment,
        }

        container: Dict[str, Any] = {
            "name": sanitized_name,
            "image": image,
            "imagePullPolicy": "IfNotPresent",
            "ports": [
                {
                    "name": "http",
                    "containerPort": port,
                    "protocol": "TCP",
                }
            ],
            "readinessProbe": {
                "httpGet": {
                    "path": health_path,
                    "port": "http",
                },
                "initialDelaySeconds": init_delay,
                "periodSeconds": period,
                "timeoutSeconds": 3,
                "successThreshold": 1,
                "failureThreshold": 3,
            },
            "livenessProbe": {
                "httpGet": {
                    "path": health_path,
                    "port": "http",
                },
                "initialDelaySeconds": init_delay * 2,
                "periodSeconds": period * 2,
                "timeoutSeconds": 3,
                "failureThreshold": 5,
            },
            "resources": {
                "requests": {
                    "cpu": "50m",
                    "memory": "64Mi",
                },
                "limits": {
                    "cpu": "500m",
                    "memory": "512Mi",
                },
            },
        }

        # Environment variables
        env_list: List[Dict[str, Any]] = [
            {"name": "PORT", "value": str(port)},
            {"name": "ENVIRONMENT", "value": environment},
            {"name": "APP_NAME", "value": application_name},
        ]
        if env_vars:
            for k, v in env_vars.items():
                env_list.append({"name": k, "value": str(v)})
        container["env"] = env_list

        if config_map_name:
            container["envFrom"] = [
                {"configMapRef": {"name": config_map_name}}
            ]

        pod_spec: Dict[str, Any] = {
            "containers": [container],
        }

        if image_pull_secret:
            pod_spec["imagePullSecrets"] = [{"name": image_pull_secret}]

        deployment: Dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": deployment_name,
                "namespace": namespace,
                "labels": labels,
                "annotations": {
                    "devforge.io/application": application_name,
                    "devforge.io/original-image": image,
                },
            },
            "spec": {
                "replicas": max(1, replicas),
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": sanitized_name,
                    }
                },
                "strategy": {
                    "type": "RollingUpdate",
                    "rollingUpdate": {
                        "maxSurge": 1,
                        "maxUnavailable": 0,
                    },
                },
                "template": {
                    "metadata": {
                        "labels": labels,
                    },
                    "spec": pod_spec,
                },
            },
        }
        return deployment

    def generate_service_dict(
        self,
        application_name: str,
        port: int = 8000,
        service_type: str = "NodePort",
        namespace: str = "devforge",
        environment: str = "development",
        node_port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate Service specification dictionary."""
        sanitized_name = sanitize_k8s_name(application_name)
        service_name = f"devforge-{sanitized_name}-svc"

        labels = {
            "app.kubernetes.io/name": sanitized_name,
            "app.kubernetes.io/instance": service_name,
            "app.kubernetes.io/part-of": "devforge",
            "app.kubernetes.io/managed-by": "devforge",
            "devforge.io/environment": environment,
        }

        service_port: Dict[str, Any] = {
            "name": "http",
            "port": port,
            "targetPort": "http",
            "protocol": "TCP",
        }
        if service_type == "NodePort" and node_port and 30000 <= node_port <= 32767:
            service_port["nodePort"] = node_port

        service: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": labels,
                "annotations": {
                    "devforge.io/application": application_name,
                },
            },
            "spec": {
                "type": service_type,
                "selector": {
                    "app.kubernetes.io/name": sanitized_name,
                },
                "ports": [service_port],
            },
        }
        return service

    def generate_configmap_dict(
        self,
        application_name: str,
        namespace: str = "devforge",
        environment: str = "development",
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate ConfigMap specification dictionary."""
        sanitized_name = sanitize_k8s_name(application_name)
        cm_name = f"devforge-{sanitized_name}-config"

        config_data = {
            "ENVIRONMENT": environment,
            "DEVFORGE_MANAGED": "true",
        }
        if data:
            config_data.update(data)

        config_map: Dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": cm_name,
                "namespace": namespace,
                "labels": {
                    "app.kubernetes.io/name": sanitized_name,
                    "app.kubernetes.io/managed-by": "devforge",
                },
            },
            "data": config_data,
        }
        return config_map

    def generate_manifest_yamls(
        self,
        application_name: str,
        image: str,
        replicas: int = 1,
        port: Optional[int] = None,
        template: Optional[str] = None,
        namespace: str = "devforge",
        environment: str = "development",
        service_type: str = "NodePort",
        image_pull_secret: Optional[str] = "devforge-ghcr-secret",
        config_data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Generate rendered YAML strings for Deployment, Service, and ConfigMap.
        Returns a dict with 'deployment', 'service', 'configmap', and 'combined'.
        """
        if not application_name or not application_name.strip():
            raise KubernetesManifestError("Application name is required to generate Kubernetes manifests")
        if not image or not image.strip():
            raise KubernetesManifestError("Container image is required to generate Kubernetes manifests")

        resolved_port = self.resolve_port(template, port)

        cm_dict = self.generate_configmap_dict(
            application_name=application_name,
            namespace=namespace,
            environment=environment,
            data=config_data,
        )
        cm_name = cm_dict["metadata"]["name"]

        dep_dict = self.generate_deployment_dict(
            application_name=application_name,
            image=image,
            replicas=replicas,
            port=resolved_port,
            template=template,
            namespace=namespace,
            environment=environment,
            image_pull_secret=image_pull_secret,
            config_map_name=cm_name,
        )

        svc_dict = self.generate_service_dict(
            application_name=application_name,
            port=resolved_port,
            service_type=service_type,
            namespace=namespace,
            environment=environment,
        )

        try:
            dep_yaml = yaml.dump(dep_dict, sort_keys=False, indent=2)
            svc_yaml = yaml.dump(svc_dict, sort_keys=False, indent=2)
            cm_yaml = yaml.dump(cm_dict, sort_keys=False, indent=2)
            combined = f"---\n{cm_yaml}---\n{dep_yaml}---\n{svc_yaml}"
        except Exception as e:
            raise KubernetesManifestError(f"Failed to serialize Kubernetes YAML manifests: {e}") from e

        return {
            "deployment": dep_yaml,
            "service": svc_yaml,
            "configmap": cm_yaml,
            "combined": combined,
            "deployment_name": dep_dict["metadata"]["name"],
            "service_name": svc_dict["metadata"]["name"],
            "port": resolved_port,
        }


manifest_generator = ManifestGenerator()
