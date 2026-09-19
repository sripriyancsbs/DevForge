output "application_name" {
  description = "The application name"
  value       = var.application_name
}

output "namespace" {
  description = "The target namespace"
  value       = var.namespace
}

output "config_map_name" {
  description = "The created application configmap"
  value       = kubernetes_config_map_v1.app_config.metadata[0].name
}

output "image" {
  description = "The full image reference"
  value       = "${var.image_repository}:${var.image_tag}"
}
