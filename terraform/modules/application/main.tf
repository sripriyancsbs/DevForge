terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
  }
}

resource "kubernetes_config_map_v1" "app_config" {
  metadata {
    name      = "devforge-${var.application_name}-iac-config"
    namespace = var.namespace
    labels = {
      "app.kubernetes.io/name"       = var.application_name
      "app.kubernetes.io/managed-by" = "terraform"
      "devforge.io/environment"      = var.environment
    }
  }

  data = {
    "APP_NAME"         = var.application_name
    "ENVIRONMENT"      = var.environment
    "IMAGE_REPOSITORY" = var.image_repository
    "IMAGE_TAG"        = var.image_tag
    "REPLICAS"         = tostring(var.replicas)
    "PORT"             = tostring(var.container_port)
  }
}
