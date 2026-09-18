export type StateStatus = 'healthy' | 'warning' | 'failed' | 'deploying' | 'pending' | 'rolled_back' | 'degraded';

export type ProvisioningState = 'PENDING' | 'PROVISIONING' | 'READY' | 'FAILED';

export interface Application {
  id: number;
  name: string;
  slug: string;
  description?: string;
  team: string;
  runtime: string;
  template?: string;
  repository_url: string;
  repository_owner?: string;
  repository_name?: string;
  repository_default_branch?: string;
  branch: string;
  environment: string;
  version: string;
  status: StateStatus;
  port: number;
  replicas: number;
  database_type?: string;
  deployment_strategy?: string;
  provisioning_status?: ProvisioningState;
  provisioning_error?: string | null;
  generated_path?: string;
  manifest_yaml?: string;
  last_deployment_at?: string;
  created_at: string;
  updated_at: string;
}

export type ProvisioningJobStep =
  | 'VALIDATE_CONFIGURATION'
  | 'PREPARE_WORKSPACE'
  | 'GENERATE_PROJECT'
  | 'GENERATE_MANIFEST'
  | 'VALIDATE_PROJECT'
  | 'CREATING_REPOSITORY'
  | 'PUSHING_REPOSITORY'
  | 'COMPLETED';

export interface GitHubStatusResponse {
  connected: boolean;
  owner: string;
  authenticated_user?: string | null;
  error?: string | null;
}

export interface ProvisioningJob {
  id: number;
  application_id: number;
  status: 'PENDING' | 'PROVISIONING' | 'READY' | 'FAILED' | 'RETRY';
  template: string;
  current_step: ProvisioningJobStep;
  attempt: number;
  max_attempts: number;
  is_retryable: boolean;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ApplicationProvisioningResponse {
  application: Application;
  provisioning_status: ProvisioningState;
  job_id?: number;
  generated_path?: string;
  manifest?: string;
  files_generated: string[];
  message: string;
}

export interface Deployment {
  id: number;
  application_id: number;
  application_name: string;
  version: string;
  commit_hash: string;
  commit_message?: string;
  environment: string;
  status: StateStatus;
  duration: string;
  triggered_by: string;
  logs?: string;
  created_at: string;
}

export interface Environment {
  id: number;
  name: string;
  slug: string;
  type: string;
  region: string;
  cluster_endpoint: string;
  status: StateStatus;
  services_count: number;
  cpu_allocated: string;
  memory_allocated: string;
  description?: string;
  created_at: string;
}

export interface ServiceHealth {
  id: number;
  service_name: string;
  status: 'healthy' | 'warning' | 'failed';
  cpu_percent: number;
  memory_mb: string;
  requests_per_sec: number;
  error_rate: string;
  uptime: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  actor: string;
  action: string;
  target: string;
  target_type: 'application' | 'deployment' | 'environment' | 'config';
  status: 'completed' | 'failed' | 'warning';
  details?: string;
  created_at: string;
}

export interface MetricCard {
  label: string;
  value: string;
  change: string;
  status: 'healthy' | 'warning' | 'failed' | 'neutral';
  subtext: string;
}

export interface OverviewMetrics {
  applications_count: number;
  healthy_services: string;
  active_deployments: number;
  failed_deployments: number;
  metrics_cards: MetricCard[];
}

export interface OverviewData {
  metrics: OverviewMetrics;
  recent_deployments: Deployment[];
  service_health: ServiceHealth[];
  recent_activity: Activity[];
}

export interface ClusterInfo {
  name: string;
  region: string;
  provider: string;
  version: string;
  nodes: number;
  cpu_utilization: string;
  memory_utilization: string;
  status: string;
}

export interface DatastoreInfo {
  name: string;
  engine: string;
  allocated_storage: string;
  connections: string;
  status: string;
}

export interface InfrastructureData {
  summary: {
    total_nodes: number;
    healthy_nodes: number;
    managed_databases: number;
    redis_caches: number;
    network_gateways: number;
    monthly_estimate: string;
  };
  clusters: ClusterInfo[];
  datastores: DatastoreInfo[];
}

export interface MonitoringData {
  global: {
    p50_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
    avg_error_rate: string;
    total_throughput_rps: number;
    slo_status: string;
  };
  service_metrics: {
    service: string;
    rps: number;
    p95_latency: string;
    error_rate: string;
    cpu: string;
    memory: string;
    status: string;
  }[];
}
