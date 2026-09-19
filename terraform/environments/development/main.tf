terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kubeconfig_context != "" ? var.kubeconfig_context : null
}

module "kubernetes_base" {
  source = "../../modules/kubernetes"

  namespace   = var.namespace
  environment = var.environment
  labels = {
    "app.kubernetes.io/managed-by" = "terraform"
    "devforge.io/environment"      = var.environment
  }
}

module "application_baseline" {
  source = "../../modules/application"

  application_name = var.application_name
  namespace        = module.kubernetes_base.namespace
  image_repository = var.image_repository
  image_tag        = var.image_tag
  replicas         = var.replicas
  container_port   = var.container_port
  environment      = var.environment
}
