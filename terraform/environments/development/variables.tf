variable "kubeconfig_path" {
  description = "Path to the kubeconfig file for cluster connection"
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "Specific kubeconfig context to use, or empty for current-context"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "development"
}

variable "namespace" {
  description = "Target Kubernetes namespace for DevForge environment"
  type        = string
  default     = "devforge"
}

variable "application_name" {
  description = "Primary baseline application name"
  type        = string
  default     = "inventory-api"
}

variable "image_repository" {
  description = "Container image repository for baseline application"
  type        = string
  default     = "ghcr.io/sripriyancsbs/inventory-api"
}

variable "image_tag" {
  description = "Container image tag for baseline application"
  type        = string
  default     = "latest"
}

variable "replicas" {
  description = "Replica count for baseline application"
  type        = number
  default     = 1
}

variable "container_port" {
  description = "Application serving port"
  type        = number
  default     = 8000
}
