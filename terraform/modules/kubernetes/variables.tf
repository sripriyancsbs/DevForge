variable "namespace" {
  description = "The Kubernetes namespace for DevForge environment resources"
  type        = string
  default     = "devforge"
}

variable "environment" {
  description = "The target deployment environment (e.g., development, staging, production)"
  type        = string
  default     = "development"
}

variable "labels" {
  description = "Labels to apply to all managed Kubernetes resources"
  type        = map(string)
  default = {
    "app.kubernetes.io/managed-by" = "terraform"
    "devforge.io/component"        = "infrastructure"
  }
}
