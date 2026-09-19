variable "application_name" {
  description = "The canonical application name"
  type        = string
}

variable "namespace" {
  description = "The Kubernetes namespace to deploy baseline application resources into"
  type        = string
  default     = "devforge"
}

variable "image_repository" {
  description = "The container image repository (e.g., ghcr.io/sripriyancsbs/inventory-api)"
  type        = string
}

variable "image_tag" {
  description = "The container image tag"
  type        = string
  default     = "latest"
}

variable "replicas" {
  description = "Desired number of pod replicas"
  type        = number
  default     = 1
  validation {
    condition     = var.replicas >= 1 && var.replicas <= 10
    error_message = "Replicas count must be between 1 and 10."
  }
}

variable "container_port" {
  description = "Port exposed by the application container"
  type        = number
  default     = 8000
  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535
    error_message = "Container port must be between 1 and 65535."
  }
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "development"
}
