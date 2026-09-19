import {
  OverviewData,
  Application,
  Deployment,
  Environment,
  InfrastructureData,
  MonitoringData,
  Activity,
  ApplicationRemediationOverview,
  RemediationPolicy,
  RemediationEvent,
  RemediationExecution,
  TerraformStatus,
  TerraformRun,
  AnsiblePlaybook,
  AnsibleExecution,
  KubernetesClusterStatus,
  KubernetesDeployment,
  CIStatusData,
  ContainerImageData,
  GitOpsApplication,
  GitOpsOperation,
  ArgoCDClusterStatus,
  SystemHealthData,
  MetricsSummaryData,
  MonitoredService,
  AlertRule,
  ScrapeTarget,
  GitHubStatusResponse,
  ApplicationProvisioningResponse
} from '../types';

export const SEED_APPLICATIONS: Application[] = [
  {
    id: 1,
    name: 'inventory-api',
    slug: 'inventory-api',
    description: 'High-performance inventory service with real-time SKU tracking and automated remediation.',
    team: 'Platform Engineering',
    runtime: 'Python 3.12 (FastAPI)',
    template: 'python-fastapi',
    repository_url: 'https://github.com/sripriyancsbs/DevForge',
    branch: 'main',
    environment: 'production',
    version: 'v1.0.2',
    status: 'healthy',
    port: 8000,
    replicas: 2,
    database_type: 'postgresql',
    deployment_strategy: 'rolling',
    provisioning_status: 'READY',
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date().toISOString(),
    last_deployment_at: new Date(Date.now() - 3600000).toISOString(),
    ci_status: 'PASSED',
    ci_workflow: 'devforge-ci.yml',
    ci_run_id: '35437276916',
    image_repository: 'ghcr.io/sripriyancsbs/inventory-api',
    image_tag: 'v1.0.2',
    image_status: 'READY'
  },
  {
    id: 2,
    name: 'billing-svc-8b3e27',
    slug: 'billing-svc-8b3e27',
    description: 'Payment settlement and subscription billing microservice.',
    team: 'Platform Engineering',
    runtime: 'Python 3.12 (FastAPI)',
    template: 'python-fastapi',
    repository_url: 'https://github.com/sripriyancsbs/DevForge',
    branch: 'main',
    environment: 'production',
    version: 'v1.0.0',
    status: 'healthy',
    port: 8000,
    replicas: 2,
    database_type: 'postgresql',
    deployment_strategy: 'rolling',
    provisioning_status: 'READY',
    created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
    updated_at: new Date().toISOString(),
    last_deployment_at: new Date(Date.now() - 7200000).toISOString(),
    ci_status: 'PASSED',
    image_status: 'READY'
  },
  {
    id: 3,
    name: 'order-svc-c5d8a5',
    slug: 'order-svc-c5d8a5',
    description: 'Order processing and lifecycle dispatch queue.',
    team: 'E-Commerce Core',
    runtime: 'Node.js 20',
    template: 'node-service',
    repository_url: 'https://github.com/sripriyancsbs/DevForge',
    branch: 'main',
    environment: 'staging',
    version: 'v2.1.0',
    status: 'healthy',
    port: 3000,
    replicas: 3,
    database_type: 'postgresql',
    deployment_strategy: 'rolling',
    provisioning_status: 'READY',
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    updated_at: new Date().toISOString(),
    last_deployment_at: new Date(Date.now() - 14400000).toISOString(),
    ci_status: 'PASSED',
    image_status: 'READY'
  },
  {
    id: 4,
    name: 'payment-gateway',
    slug: 'payment-gateway',
    description: 'PCI-compliant card payment and merchant settlement router.',
    team: 'Finance Tech',
    runtime: 'Go 1.22',
    template: 'go-microservice',
    repository_url: 'https://github.com/sripriyancsbs/DevForge',
    branch: 'main',
    environment: 'production',
    version: 'v3.0.1',
    status: 'healthy',
    port: 8080,
    replicas: 4,
    database_type: 'none',
    deployment_strategy: 'canary',
    provisioning_status: 'READY',
    created_at: new Date(Date.now() - 86400000 * 6).toISOString(),
    updated_at: new Date().toISOString(),
    last_deployment_at: new Date(Date.now() - 18000000).toISOString(),
    ci_status: 'PASSED',
    image_status: 'READY'
  }
];

export const SEED_OVERVIEW: OverviewData = {
  metrics: {
    applications_count: 4,
    healthy_services: '4/4',
    active_deployments: 1,
    failed_deployments: 0,
    metrics_cards: [
      {
        label: 'Healthy Services',
        value: '100%',
        change: '+0.0%',
        status: 'healthy',
        subtext: '4 of 4 operational'
      },
      {
        label: 'Deployment Frequency',
        value: '12 / day',
        change: '+24%',
        status: 'healthy',
        subtext: 'Rolling deploys'
      },
      {
        label: 'MTTR (Self-Healing)',
        value: '18s',
        change: '-45%',
        status: 'healthy',
        subtext: 'Phase 11 automated'
      },
      {
        label: 'Platform Availability',
        value: '99.98%',
        change: '+0.02%',
        status: 'healthy',
        subtext: 'SLO compliant'
      }
    ]
  },
  recent_deployments: [
    {
      id: 101,
      application_id: 1,
      application_name: 'inventory-api',
      version: 'v1.0.2',
      environment: 'production',
      status: 'healthy',
      commit_hash: '6e3f5f6',
      commit_message: 'feat: Phase 11 self-healing and automated remediation with responsive layout fixes',
      triggered_by: 'sripriyancsbs',
      duration: '42s',
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 102,
      application_id: 2,
      application_name: 'billing-svc-8b3e27',
      version: 'v1.0.0',
      environment: 'production',
      status: 'healthy',
      commit_hash: '1881327',
      commit_message: 'ci: release v1.0.0',
      triggered_by: 'system',
      duration: '31s',
      created_at: new Date(Date.now() - 7200000).toISOString()
    }
  ],
  service_health: [
    {
      id: 1,
      service_name: 'inventory-api',
      status: 'healthy',
      cpu_percent: 18.4,
      memory_mb: '184 MB',
      requests_per_sec: 142,
      error_rate: '0.00%',
      uptime: '99.98%',
      updated_at: new Date().toISOString()
    },
    {
      id: 2,
      service_name: 'billing-svc-8b3e27',
      status: 'healthy',
      cpu_percent: 14.1,
      memory_mb: '142 MB',
      requests_per_sec: 88,
      error_rate: '0.00%',
      uptime: '99.99%',
      updated_at: new Date().toISOString()
    }
  ],
  recent_activity: [
    {
      id: 1,
      action: 'Self-Healing Automated Recovery',
      target: 'inventory-api',
      target_type: 'application',
      actor: 'self-healing-engine',
      status: 'completed',
      details: 'Auto-recovered crash loop state via allowlisted RESTART_POD action.',
      created_at: new Date(Date.now() - 14200000).toISOString()
    },
    {
      id: 2,
      action: 'Deployment Completed',
      target: 'inventory-api',
      target_type: 'deployment',
      actor: 'sripriyancsbs',
      status: 'completed',
      details: 'Version v1.0.2 deployed to production successfully.',
      created_at: new Date(Date.now() - 3600000).toISOString()
    }
  ]
};

export const SEED_ENVIRONMENTS: Environment[] = [
  {
    id: 1,
    name: 'development',
    slug: 'development',
    type: 'development',
    region: 'us-east-1',
    cluster_endpoint: 'https://k8s-dev.devforge.internal',
    status: 'healthy',
    services_count: 2,
    cpu_allocated: '2 Cores',
    memory_allocated: '4 GB',
    description: 'Local KinD development cluster',
    created_at: new Date(Date.now() - 86400000 * 30).toISOString()
  },
  {
    id: 2,
    name: 'staging',
    slug: 'staging',
    type: 'staging',
    region: 'us-east-1',
    cluster_endpoint: 'https://k8s-staging.devforge.internal',
    status: 'healthy',
    services_count: 3,
    cpu_allocated: '4 Cores',
    memory_allocated: '8 GB',
    description: 'Pre-production staging cluster',
    created_at: new Date(Date.now() - 86400000 * 30).toISOString()
  },
  {
    id: 3,
    name: 'production',
    slug: 'production',
    type: 'production',
    region: 'us-east-1',
    cluster_endpoint: 'https://k8s-prod.devforge.internal',
    status: 'healthy',
    services_count: 4,
    cpu_allocated: '8 Cores',
    memory_allocated: '16 GB',
    description: 'Production Kubernetes cluster',
    created_at: new Date(Date.now() - 86400000 * 30).toISOString()
  }
];

export const SEED_DEPLOYMENTS: Deployment[] = [
  {
    id: 101,
    application_id: 1,
    application_name: 'inventory-api',
    version: 'v1.0.2',
    environment: 'production',
    status: 'healthy',
    commit_hash: '6e3f5f6',
    commit_message: 'feat: Phase 11 self-healing and automated remediation with responsive layout fixes',
    triggered_by: 'sripriyancsbs',
    duration: '42s',
    logs: '[2026-09-19T10:28:32Z] [INFO] Deployment initialized for revision v1.0.2\n[2026-09-19T10:28:45Z] [INFO] Kubernetes pods rolled out successfully.\n[2026-09-19T10:29:00Z] [INFO] Probes passing. Status: HEALTHY.',
    created_at: new Date(Date.now() - 3600000).toISOString()
  },
  {
    id: 100,
    application_id: 1,
    application_name: 'inventory-api',
    version: 'v1.0.1',
    environment: 'production',
    status: 'healthy',
    commit_hash: '58c6f18',
    commit_message: 'feat: initial Phase 11 self-healing',
    triggered_by: 'system',
    duration: '38s',
    logs: '[INFO] Rollout completed successfully.',
    created_at: new Date(Date.now() - 86400000).toISOString()
  }
];

export const SEED_POLICIES: RemediationPolicy[] = [
  {
    id: 1,
    name: 'High CPU Throttle Recovery',
    event_type: 'HIGH_ERROR_RATE',
    environment: 'production',
    action: 'RESTART_POD',
    enabled: true,
    max_attempts: 3,
    cooldown_seconds: 60,
    requires_approval: false,
    description: 'Restarts pod if elevated error rates are detected in production.'
  },
  {
    id: 2,
    name: 'Pod Crash Loop Recycling',
    event_type: 'POD_CRASH_LOOP',
    environment: 'production',
    action: 'RESTART_POD',
    enabled: true,
    max_attempts: 2,
    cooldown_seconds: 120,
    requires_approval: false,
    description: 'Recycles failing container instances experiencing crash loops.'
  },
  {
    id: 3,
    name: 'Health Check Failure Rollback',
    event_type: 'APPLICATION_UNHEALTHY',
    environment: 'production',
    action: 'ROLLBACK_DEPLOYMENT',
    enabled: true,
    max_attempts: 1,
    cooldown_seconds: 300,
    requires_approval: true,
    description: 'Triggers automated rollback after confirmation if application endpoints are unhealthy.'
  }
];

export const SEED_EXECUTIONS: RemediationExecution[] = [
  {
    id: 1,
    event_id: 1,
    application_id: 1,
    environment_id: 'production',
    action: 'RESTART_POD',
    attempt: 1,
    status: 'SUCCESS',
    started_at: new Date(Date.now() - 14350000).toISOString(),
    completed_at: new Date(Date.now() - 14200000).toISOString(),
    created_at: new Date(Date.now() - 14350000).toISOString()
  }
];

export const SEED_EVENTS: RemediationEvent[] = [
  {
    id: 1,
    application_id: 1,
    environment_id: 'production',
    event_type: 'POD_CRASH_LOOP',
    source: 'KubernetesWatcher',
    severity: 'HIGH',
    status: 'RECOVERED',
    detected_at: new Date(Date.now() - 14400000).toISOString(),
    details: 'Pod entered CrashLoopBackOff state. Successfully restored via automated restart policy.',
    attempts: 1,
    resolved_at: new Date(Date.now() - 14200000).toISOString(),
    created_at: new Date(Date.now() - 14400000).toISOString(),
    executions: SEED_EXECUTIONS
  }
];

export const SEED_REMEDIATION: ApplicationRemediationOverview = {
  application_id: 1,
  application_name: 'inventory-api',
  health_status: 'HEALTHY',
  active_events_count: 0,
  total_remediations: 4,
  successful_remediations: 4,
  failed_remediations: 0,
  last_remediation: SEED_EXECUTIONS[0],
  policies: SEED_POLICIES,
  events: SEED_EVENTS
};

export const SEED_ACTIVITY: Activity[] = [
  {
    id: 1,
    action: 'Self-Healing Automated Recovery',
    target: 'inventory-api',
    target_type: 'application',
    actor: 'self-healing-engine',
    status: 'completed',
    details: 'Auto-recovered crash loop state via allowlisted RESTART_POD action.',
    created_at: new Date(Date.now() - 14200000).toISOString()
  },
  {
    id: 2,
    action: 'Deployment Completed',
    target: 'inventory-api',
    target_type: 'deployment',
    actor: 'sripriyancsbs',
    status: 'completed',
    details: 'Version v1.0.2 deployed to production successfully.',
    created_at: new Date(Date.now() - 3600000).toISOString()
  },
  {
    id: 3,
    action: 'Application Registered',
    target: 'billing-svc-8b3e27',
    target_type: 'application',
    actor: 'platform-admin',
    status: 'completed',
    details: 'Created via FastAPI template with PostgreSQL dependency.',
    created_at: new Date(Date.now() - 86400000).toISOString()
  }
];

export const SEED_INFRASTRUCTURE: InfrastructureData = {
  summary: {
    total_nodes: 9,
    healthy_nodes: 9,
    managed_databases: 1,
    redis_caches: 1,
    network_gateways: 2,
    monthly_estimate: '$148.00'
  },
  clusters: [
    {
      name: 'local-kind',
      region: 'localhost',
      provider: 'KinD',
      version: 'v1.31.0',
      nodes: 3,
      status: 'active',
      cpu_utilization: '24%',
      memory_utilization: '41%'
    },
    {
      name: 'prod-eks',
      region: 'us-east-1',
      provider: 'AWS EKS',
      version: 'v1.30.2',
      nodes: 6,
      status: 'active',
      cpu_utilization: '32%',
      memory_utilization: '58%'
    }
  ],
  datastores: [
    {
      name: 'devforge-postgres',
      engine: 'PostgreSQL 16',
      status: 'online',
      allocated_storage: '50 GB',
      connections: '12 active'
    }
  ]
};

export const SEED_MONITORING: MonitoringData = {
  global: {
    p50_latency_ms: 12.4,
    p95_latency_ms: 38.2,
    p99_latency_ms: 74.8,
    avg_error_rate: '0.01%',
    total_throughput_rps: 230,
    slo_status: '99.98%'
  },
  service_metrics: [
    {
      service: 'inventory-api',
      rps: 142,
      p95_latency: '24ms',
      error_rate: '0.00%',
      cpu: '18%',
      memory: '184 MB',
      status: 'healthy'
    },
    {
      service: 'billing-svc-8b3e27',
      rps: 88,
      p95_latency: '31ms',
      error_rate: '0.00%',
      cpu: '14%',
      memory: '142 MB',
      status: 'healthy'
    }
  ]
};

export const SEED_TERRAFORM_STATUS: TerraformStatus = {
  installed: true,
  version: '1.7.0',
  provider: 'hashicorp/kubernetes',
  environment: 'production',
  status: 'APPLIED',
  last_operation: 'apply',
  resources_count: 6,
  latest_run: {
    id: 1,
    environment: 'production',
    operation: 'apply',
    status: 'APPLIED',
    plan_output: 'No changes. Your infrastructure matches the configuration.',
    apply_output: 'Apply complete! Resources: 0 added, 0 changed, 0 destroyed.',
    resources_count: 6,
    error_message: null,
    started_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 86395000).toISOString(),
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86395000).toISOString()
  }
};

export const SEED_TERRAFORM_RUNS: TerraformRun[] = [
  {
    id: 1,
    environment: 'production',
    operation: 'apply',
    status: 'APPLIED',
    plan_output: 'No changes. Your infrastructure matches the configuration.',
    apply_output: 'Apply complete! Resources: 0 added, 0 changed, 0 destroyed.',
    resources_count: 6,
    error_message: null,
    started_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 86395000).toISOString(),
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86395000).toISOString()
  }
];

export const SEED_ANSIBLE_PLAYBOOKS: AnsiblePlaybook[] = [
  {
    name: 'site-baseline.yml',
    title: 'Site Baseline Security & Networking',
    description: 'Configures kernel sysctl parameters, firewall baseline, and node NTP synchronizers.',
    file: 'ansible/playbooks/site-baseline.yml',
    scope: 'environment',
    required_params: ['environment_id'],
    optional_params: ['dry_run']
  },
  {
    name: 'k8s-node-hardening.yml',
    title: 'Kubernetes Node Hardening',
    description: 'Enforces CIS benchmark hardening across all cluster worker nodes.',
    file: 'ansible/playbooks/k8s-node-hardening.yml',
    scope: 'environment',
    required_params: ['environment_id'],
    optional_params: []
  }
];

export const SEED_ANSIBLE_EXECUTIONS: AnsibleExecution[] = [
  {
    id: 1,
    playbook_name: 'site-baseline.yml',
    application_id: 1,
    application_name: 'inventory-api',
    environment_id: 'production',
    status: 'SUCCESS',
    duration_seconds: 14,
    output: 'PLAY [Apply baseline security]\nTASK [Gathering Facts] ... ok\nPLAY RECAP: localhost : ok=4 changed=1 unreachable=0 failed=0',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 3586000).toISOString(),
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3586000).toISOString()
  }
];

export const SEED_KUBERNETES_STATUS: KubernetesClusterStatus = {
  connected: true,
  provider: 'KinD',
  version: 'v1.31.0',
  namespace: 'devforge',
  node_count: 3,
  nodes: [
    {
      name: 'devforge-control-plane',
      ready: true,
      kubelet_version: 'v1.31.0',
      os_image: 'Ubuntu 22.04 LTS'
    },
    {
      name: 'devforge-worker',
      ready: true,
      kubelet_version: 'v1.31.0',
      os_image: 'Ubuntu 22.04 LTS'
    },
    {
      name: 'devforge-worker2',
      ready: true,
      kubelet_version: 'v1.31.0',
      os_image: 'Ubuntu 22.04 LTS'
    }
  ]
};

export const SEED_KUBERNETES_DEPLOYMENT: KubernetesDeployment = {
  id: 1,
  application_id: 1,
  application_name: 'inventory-api',
  environment: 'production',
  namespace: 'devforge',
  deployment_name: 'inventory-api-deployment',
  service_name: 'inventory-api-service',
  image: 'ghcr.io/sripriyancsbs/inventory-api:v1.0.2',
  image_repository: 'ghcr.io/sripriyancsbs/inventory-api',
  image_tag: 'v1.0.2',
  replicas: 2,
  ready_replicas: 2,
  status: 'RUNNING',
  port: 8000,
  pods: [
    {
      name: 'inventory-api-6b797fc7b8-8jpx2',
      phase: 'Running',
      ready: true,
      restart_count: 0
    },
    {
      name: 'inventory-api-6b797fc7b8-v8mnq',
      phase: 'Running',
      ready: true,
      restart_count: 0
    }
  ]
};

export const SEED_GITOPS_APPLICATION: GitOpsApplication = {
  id: 1,
  application_id: 1,
  application_name: 'inventory-api',
  argocd_application_name: 'devforge-inventory-api',
  git_repository: 'https://github.com/sripriyancsbs/DevForge',
  git_path: 'gitops/apps/inventory-api/overlays/production',
  target_revision: 'main',
  namespace: 'devforge',
  sync_status: 'SYNCED',
  health_status: 'HEALTHY',
  auto_sync_enabled: true,
  self_heal_enabled: true,
  drift_count: 0,
  drifted_resources: [],
  created_at: new Date(Date.now() - 86400000).toISOString(),
  updated_at: new Date().toISOString()
};

export const SEED_ARGOCD_STATUS: ArgoCDClusterStatus = {
  available: true,
  version: 'v2.10.4',
  server_url: 'https://argocd.devforge.internal',
  namespace: 'argocd'
};

export const SEED_CONTAINER_IMAGE: ContainerImageData = {
  id: 1,
  application_id: 1,
  registry: 'ghcr.io',
  repository: 'sripriyancsbs/inventory-api',
  tag: 'v1.0.2',
  digest: 'sha256:4a5c6d7e8f90123456789abcdef0123456789abcdef0123456789abcdef01234',
  status: 'READY',
  created_at: new Date().toISOString()
};

export const SEED_CI_STATUS: CIStatusData = {
  application_id: 1,
  application_name: 'inventory-api',
  status: 'PASSED',
  workflow: 'devforge-ci.yml',
  run_id: '35437276916',
  run_url: 'https://github.com/sripriyancsbs/DevForge/actions/runs/35437276916',
  last_run_at: new Date().toISOString()
};

export const SEED_GITHUB_STATUS: GitHubStatusResponse = {
  connected: true,
  owner: 'sripriyancsbs',
  authenticated_user: 'sripriyancsbs'
};

export const SEED_MANIFEST_YAML = `apiVersion: devforge.io/v1alpha1
kind: Application
metadata:
  name: inventory-api
  namespace: devforge
spec:
  runtime: python
  version: v1.0.2
  port: 8000
  replicas: 2
  strategy: rolling
  health:
    endpoint: /healthz
    periodSeconds: 10
`;
