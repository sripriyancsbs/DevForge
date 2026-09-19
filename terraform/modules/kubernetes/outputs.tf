output "namespace" {
  description = "The created Kubernetes namespace name"
  value       = kubernetes_namespace_v1.devforge.metadata[0].name
}

output "config_map_name" {
  description = "The created baseline environment ConfigMap name"
  value       = kubernetes_config_map_v1.environment_config.metadata[0].name
}

output "environment" {
  description = "The target environment"
  value       = var.environment
}
