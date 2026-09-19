terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
  }
}

resource "kubernetes_namespace_v1" "devforge" {
  metadata {
    name = var.namespace
    labels = merge(var.labels, {
      "name"                    = var.namespace
      "devforge.io/environment" = var.environment
    })
  }
}

resource "kubernetes_config_map_v1" "environment_config" {
  metadata {
    name      = "devforge-env-config"
    namespace = kubernetes_namespace_v1.devforge.metadata[0].name
    labels = merge(var.labels, {
      "devforge.io/environment" = var.environment
    })
  }

  data = {
    "ENVIRONMENT"      = var.environment
    "MANAGED_BY"       = "terraform"
    "DEVFORGE_VERSION" = "1.0.0"
  }
}
