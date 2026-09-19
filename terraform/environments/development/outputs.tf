output "environment" {
  description = "The target environment"
  value       = var.environment
}

output "namespace" {
  description = "The Kubernetes namespace managed by Terraform"
  value       = module.kubernetes_base.namespace
}

output "application_name" {
  description = "The baseline application name"
  value       = module.application_baseline.application_name
}

output "image" {
  description = "The configured application container image"
  value       = module.application_baseline.image
}

output "config_map_name" {
  description = "The application configmap name created by Terraform"
  value       = module.application_baseline.config_map_name
}
