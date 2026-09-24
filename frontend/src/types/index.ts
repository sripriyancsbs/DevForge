export type StateStatus = 'healthy' | 'warning' | 'failed' | 'deploying' | 'pending' | 'rolled_back' | 'degraded';

export type ProvisioningState = 'PENDING' | 'PROVISIONING' | 'READY' | 'FAILED';

export interface Application {
  id: number;
  workspace_id?: number | null;
  name: string;
  slug: string;
  description?: string;
  team: string;
  runtime: string;
  template?: string;
  template_id?: string;
  template_version?: string;
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
  ci_status?: 'UNKNOWN' | 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED';
  ci_workflow?: string;
  ci_run_id?: string | null;
  ci_run_url?: string | null;
  ci_last_run_at?: string | null;
  image_repository?: string | null;
  image_tag?: string | null;
  image_digest?: string | null;
  image_status?: 'PENDING' | 'BUILDING' | 'PUSHING' | 'READY' | 'FAILED';
  last_deployment_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ContainerImageData {
  id?: number;
  application_id: number;
  registry: string;
  repository: string;
  tag: string;
  digest?: string | null;
  commit_sha?: string | null;
  status: 'PENDING' | 'BUILDING' | 'PUSHING' | 'READY' | 'FAILED';
  created_at?: string | null;
  updated_at?: string | null;
  image_repository?: string;
  image_tag?: string;
  image_digest?: string | null;
}

export type ProvisioningJobStep =
  | 'VALIDATE_CONFIGURATION'
  | 'PREPARE_WORKSPACE'
  | 'GENERATE_PROJECT'
  | 'GENERATE_MANIFEST'
  | 'GENERATING_CI_WORKFLOW'
  | 'VALIDATE_PROJECT'
  | 'CREATING_REPOSITORY'
  | 'PUSHING_REPOSITORY'
  | 'COMPLETED';

export interface CIStatusData {
  status: 'UNKNOWN' | 'QUEUED' | 'RUNNING' | 'PASSED' | 'FAILED';
  workflow: string;
  run_id: string | null;
  run_url: string | null;
  last_run_at: string | null;
  application_id: number;
  application_name: string;
}

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

export interface PodStatusDetail {
  name: string;
  phase: string;
  ready: boolean;
  restart_count: number;
  node_name?: string | null;
  started_at?: string | null;
  message?: string | null;
}

export interface KubernetesDeployment {
  id: number;
  application_id: number;
  application_name: string;
  environment: string;
  namespace: string;
  deployment_name: string;
  service_name: string;
  image: string;
  image_repository: string;
  image_tag: string;
  replicas: number;
  ready_replicas: number;
  status: 'PENDING' | 'DEPLOYING' | 'RUNNING' | 'FAILED' | 'STOPPED';
  port: number;
  node_port?: number | null;
  service_url?: string | null;
  manifest_yaml?: string | null;
  error_message?: string | null;
  pods: PodStatusDetail[];
  created_at?: string;
  updated_at?: string;
}

export interface KubernetesClusterStatus {
  connected: boolean;
  provider: string;
  version?: string | null;
  namespace: string;
  node_count: number;
  nodes: {
    name: string;
    ready: boolean;
    kubelet_version: string;
    os_image: string;
  }[];
  error?: string | null;
}

export interface TerraformRun {
  id: number;
  environment: string;
  operation: string;
  status: string;
  plan_output: string | null;
  apply_output: string | null;
  resources_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TerraformStatus {
  installed: boolean;
  version: string | null;
  provider: string;
  environment: string;
  status: string;
  last_operation: string | null;
  resources_count: number;
  latest_run: TerraformRun | null;
}

export interface TerraformPlanResponse {
  run_id: number;
  environment: string;
  status: string;
  summary: {
    to_add: number;
    to_change: number;
    to_destroy: number;
    resources: Array<{
      action: string;
      type: string;
      name: string;
      symbol: string;
    }>;
  };
  plan_output: string;
  created_at: string;
}

// =============================================================================
// Phase 8: Ansible Automation Interfaces
// =============================================================================
export interface AnsiblePlaybook {
  name: string;
  title: string;
  description: string;
  file: string;
  scope: 'application' | 'environment' | 'all';
  required_params: string[];
  optional_params: string[];
}

export interface AnsibleExecution {
  id: number;
  application_id?: number | null;
  application_name?: string | null;
  environment_id: string;
  playbook_name: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  output?: string | null;
  error_output?: string | null;
  return_code?: number | null;
  duration_seconds?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAnsibleExecutionRequest {
  playbook_name: string;
  application_id?: number | null;
  environment_id: string;
}

// =============================================================================
// Phase 9: Observability & Prometheus/Grafana Interfaces
// =============================================================================
export interface SystemHealthData {
  status: 'healthy' | 'degraded' | 'critical';
  timestamp: string;
  backend: {
    status: string;
    version: string;
    uptime_seconds: number;
    port: number;
    environment: string;
  };
  worker: {
    status: string;
    metrics_port: number;
    active_jobs: number;
    heartbeat_seconds_ago?: number | null;
    concurrency: number;
  };
  database: {
    status: string;
    engine: string;
    active_connections: number;
    latency_ms: number;
    database_name: string;
  };
  kubernetes: {
    status: string;
    cluster_name: string;
    namespace: string;
    nodes_count: number;
  };
  prometheus: {
    status: string;
    url: string;
    scrape_interval: string;
    active_targets: number;
  };
  grafana: {
    status: string;
    url: string;
    version: string;
    dashboard_uid: string;
    dashboard_url: string;
  };
}

export interface MetricsSummaryData {
  api: {
    total_requests: number;
    total_errors: number;
    error_rate_percent: number;
    active_requests: number;
    p95_latency_ms: number;
    throughput_rps: number;
  };
  applications: {
    total: number;
    healthy: number;
    failed: number;
  };
  provisioning: {
    total_jobs: number;
    succeeded: number;
    failed: number;
    pending: number;
    success_rate_percent: number;
  };
  deployments: {
    total: number;
    healthy: number;
    failed: number;
  };
  ansible: {
    total_executions: number;
    succeeded: number;
    failed: number;
    success_rate_percent: number;
  };
  infrastructure: {
    terraform_status: string;
    managed_resources_count: number;
  };
}

export interface MonitoredService {
  name: string;
  component: string;
  tier: string;
  endpoint: string;
  port: number;
  health: string;
  latency_ms?: number | null;
  description: string;
}

export interface AlertRule {
  name: string;
  state: string;
  severity: string;
  summary: string;
  description: string;
  expression: string;
}

export interface ScrapeTarget {
  job: string;
  instance: string;
  health: string;
  last_scrape?: string;
  last_duration_seconds?: number;
  scrape_url: string;
}

// =============================================================================
// Phase 10: GitOps & Argo CD Interfaces
// =============================================================================
export type GitOpsSyncStatus = 'SYNCED' | 'OUT_OF_SYNC' | 'SYNCING' | 'UNKNOWN';
export type GitOpsHealthStatus = 'HEALTHY' | 'PROGRESSING' | 'DEGRADED' | 'MISSING' | 'UNKNOWN';

export interface GitOpsDriftedResource {
  group: string;
  kind: string;
  name: string;
  namespace: string;
  hook: boolean;
}

export interface GitOpsApplication {
  id: number;
  application_id: number;
  application_name: string;
  argocd_application_name: string;
  git_repository: string;
  git_path: string;
  target_revision: string;
  namespace: string;
  sync_status: GitOpsSyncStatus;
  health_status: GitOpsHealthStatus;
  auto_sync_enabled: boolean;
  self_heal_enabled: boolean;
  last_synced_at?: string | null;
  last_sync_revision?: string | null;
  sync_message?: string | null;
  drift_count: number;
  drifted_resources: GitOpsDriftedResource[];
  created_at: string;
  updated_at: string;
}

export interface GitOpsOperation {
  id: number;
  gitops_application_id: number;
  operation_type: 'ENABLE' | 'SYNC' | 'REFRESH';
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  revision?: string | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArgoCDClusterStatus {
  available: boolean;
  version: string;
  server_url: string;
  namespace: string;
}

export interface EnableGitOpsRequest {
  git_repository?: string;
  git_path?: string;
  target_revision?: string;
  namespace?: string;
  auto_sync?: boolean;
  self_heal?: boolean;
}

// =============================================================================
// Phase 11: Self-Healing and Automated Remediation Interfaces
// =============================================================================
export type RemediationEventType =
  | 'APPLICATION_UNHEALTHY'
  | 'APPLICATION_UNAVAILABLE'
  | 'POD_CRASH_LOOP'
  | 'DEPLOYMENT_FAILED'
  | 'DEPLOYMENT_STUCK'
  | 'GITOPS_OUT_OF_SYNC'
  | 'HIGH_ERROR_RATE';

export type RemediationEventStatus =
  | 'DETECTED'
  | 'EVALUATING'
  | 'REMEDIATING'
  | 'VERIFYING'
  | 'RECOVERED'
  | 'FAILED'
  | 'IGNORED'
  | 'ESCALATED'
  | 'APPROVED'
  | 'CANCELLED';

export type RemediationExecutionStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'SUCCESS'
  | 'FAILED'
  | 'CANCELLED';

export interface RemediationPolicy {
  id: number;
  name: string;
  event_type: string;
  environment: string;
  action: string;
  enabled: boolean;
  max_attempts: number;
  cooldown_seconds: number;
  requires_approval: boolean;
  description?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface RemediationExecution {
  id: number;
  event_id: number;
  application_id: number;
  environment_id: string;
  policy_id?: number | null;
  action: string;
  status: RemediationExecutionStatus;
  attempt: number;
  started_at?: string | null;
  completed_at?: string | null;
  result?: string | null;
  error_message?: string | null;
  created_at?: string;
}

export interface RemediationEvent {
  id: number;
  application_id: number;
  environment_id: string;
  event_type: RemediationEventType;
  source: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: RemediationEventStatus;
  detected_at?: string;
  details?: string | null;
  attempts: number;
  resolved_at?: string | null;
  created_at: string;
  executions?: RemediationExecution[];
}

export interface ApplicationRemediationOverview {
  application_id: number;
  application_name: string;
  health_status: string;
  active_events_count: number;
  total_remediations: number;
  successful_remediations: number;
  failed_remediations: number;
  last_remediation?: RemediationExecution | null;
  events: RemediationEvent[];
  policies: RemediationPolicy[];
}

// Phase 12 RBAC & Authentication Types
export type Role = 'ADMIN' | 'OPERATOR' | 'DEVELOPER' | 'VIEWER';

export interface User {
  id: number;
  username: string;
  email: string;
  display_name?: string;
  role: Role;
  is_active: boolean;
  status?: string;
  created_at?: string;
  last_login_at?: string;
  permissions?: string[];
  workspaces?: UserWorkspaceInfo[];
  active_workspace?: UserWorkspaceInfo;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Phase 14 Real User, Workspace & RBAC Types
export interface UserWorkspaceInfo {
  id: number;
  name: string;
  slug: string;
  role: string;
}

export interface Workspace {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
  current_user_role?: string;
  member_count?: number;
  application_count?: number;
}

export interface WorkspaceMember {
  id: number;
  workspace_id: number;
  user_id: number;
  username?: string;
  email?: string;
  display_name?: string;
  role: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface AddWorkspaceMemberPayload {
  email: string;
  role: string;
  name?: string;
  username?: string;
  display_name?: string;
  password?: string;
  confirm_password?: string;
}

// Phase 13 Template System Types
export interface ApplicationTemplate {
  id?: number | string;
  template_id: string;
  name: string;
  description?: string;
  runtime: string;
  framework: string;
  version: string;
  supported_environments: string[];
  generated_project_structure: string[];
  required_variables: string[];
  optional_variables: Record<string, any>;
  default_values: Record<string, any>;
  validation_rules: Record<string, any>;
  is_enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TemplatePreviewResponse {
  template_id: string;
  template_name: string;
  template_version: string;
  runtime: string;
  framework: string;
  application_name: string;
  environment: string;
  files: string[];
  manifest_preview: string;
  key_generated_components?: string[];
}
