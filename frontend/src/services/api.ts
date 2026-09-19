import {
  OverviewData,
  Application,
  ApplicationProvisioningResponse,
  Deployment,
  Environment,
  InfrastructureData,
  MonitoringData,
  Activity,
  ProvisioningJob,
  GitHubStatusResponse,
  CIStatusData,
  ContainerImageData,
  KubernetesDeployment,
  KubernetesClusterStatus,
  TerraformStatus,
  TerraformPlanResponse,
  TerraformRun,
  AnsiblePlaybook,
  AnsibleExecution,
  CreateAnsibleExecutionRequest,
  SystemHealthData,
  MetricsSummaryData,
  MonitoredService,
  AlertRule,
  ScrapeTarget,
  GitOpsApplication,
  GitOpsOperation,
  ArgoCDClusterStatus,
  EnableGitOpsRequest,
  ApplicationRemediationOverview,
  RemediationEvent,
  RemediationPolicy,
  RemediationExecution
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

export const api = {
  async getOverview(): Promise<OverviewData> {
    const res = await fetch(`${API_BASE}/overview`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch overview`);
    return res.json();
  },

  async getApplications(params?: { search?: string; status?: string; environment?: string }): Promise<Application[]> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.environment && params.environment !== 'all') searchParams.append('environment', params.environment);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const res = await fetch(`${API_BASE}/applications${qs}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch applications`);
    return res.json();
  },

  async getApplicationDetails(idOrSlug: string | number): Promise<{ application: Application; deployments: Deployment[]; health: any }> {
    const res = await fetch(`${API_BASE}/applications/${idOrSlug}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch app details`);
    return res.json();
  },

  async getApplicationManifest(idOrSlug: string | number): Promise<string> {
    const res = await fetch(`${API_BASE}/applications/${idOrSlug}/manifest`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch devforge.yaml manifest`);
    return res.text();
  },

  async createApplication(data: {
    name: string;
    description?: string;
    team?: string;
    runtime?: string;
    template?: string;
    repository_url?: string;
    branch?: string;
    environment?: string;
    database_type?: string;
    deployment_strategy?: string;
    version?: string;
    port?: number;
    replicas?: number;
  }): Promise<ApplicationProvisioningResponse> {
    const res = await fetch(`${API_BASE}/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Provisioning failed' }));
      let msg = err.detail || 'Failed to provision application';
      if (err.errors && Array.isArray(err.errors)) {
        msg = err.errors.map((e: any) => `${e.field}: ${e.message}`).join(', ');
      }
      throw new Error(msg);
    }
    return res.json();
  },

  async getDeployments(params?: { status?: string; environment?: string; application_id?: number }): Promise<Deployment[]> {
    const searchParams = new URLSearchParams();
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.environment && params.environment !== 'all') searchParams.append('environment', params.environment);
    if (params?.application_id) searchParams.append('application_id', String(params.application_id));

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const res = await fetch(`${API_BASE}/deployments${qs}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch deployments`);
    return res.json();
  },

  async triggerDeployment(data: { application_id: number; version: string; environment: string; commit_message?: string }): Promise<Deployment> {
    const res = await fetch(`${API_BASE}/deployments/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to trigger deployment');
    return res.json();
  },

  async getEnvironments(): Promise<Environment[]> {
    const res = await fetch(`${API_BASE}/environments`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch environments`);
    return res.json();
  },

  async getActivity(params?: { target_type?: string; status?: string; application?: string }): Promise<Activity[]> {
    const searchParams = new URLSearchParams();
    if (params?.target_type && params.target_type !== 'all') searchParams.append('target_type', params.target_type);
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.application && params.application !== 'all') searchParams.append('application', params.application);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const res = await fetch(`${API_BASE}/activity${qs}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch activity`);
    return res.json();
  },

  async getInfrastructure(): Promise<InfrastructureData> {
    const res = await fetch(`${API_BASE}/infrastructure`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch infrastructure`);
    return res.json();
  },

  async getMonitoring(): Promise<MonitoringData> {
    const res = await fetch(`${API_BASE}/monitoring`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch monitoring`);
    return res.json();
  },

  async getProvisioningJob(jobId: number): Promise<ProvisioningJob> {
    const res = await fetch(`${API_BASE}/provisioning/${jobId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch provisioning job #${jobId}`);
    return res.json();
  },

  async retryProvisioningJob(jobId: number): Promise<ProvisioningJob> {
    const res = await fetch(`${API_BASE}/provisioning/${jobId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to retry provisioning job #${jobId}`);
    return res.json();
  },

  async getLatestJobForApplication(appId: number): Promise<ProvisioningJob> {
    const res = await fetch(`${API_BASE}/provisioning/by-app/${appId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch job for application #${appId}`);
    return res.json();
  },

  async getGitHubStatus(): Promise<GitHubStatusResponse> {
    const res = await fetch(`${API_BASE}/integrations/github/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch GitHub status`);
    return res.json();
  },

  async reprovisionApplication(appId: number): Promise<ApplicationProvisioningResponse> {
    const res = await fetch(`${API_BASE}/applications/${appId}/provision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to trigger reprovisioning' }));
      throw new Error(err.detail || 'Failed to trigger reprovisioning');
    }
    return res.json();
  },

  async getApplicationCI(appId: number): Promise<CIStatusData> {
    const res = await fetch(`${API_BASE}/applications/${appId}/ci`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch CI status for application #${appId}`);
    return res.json();
  },

  async refreshApplicationCI(appId: number): Promise<CIStatusData> {
    const res = await fetch(`${API_BASE}/applications/${appId}/ci/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to refresh CI status for application #${appId}`);
    return res.json();
  },

  async getApplicationImages(appId: number): Promise<{ images: ContainerImageData[]; total: number; latest?: ContainerImageData }> {
    const res = await fetch(`${API_BASE}/applications/${appId}/images`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch images for application #${appId}`);
    return res.json();
  },

  async getLatestApplicationImage(appId: number): Promise<ContainerImageData> {
    const res = await fetch(`${API_BASE}/applications/${appId}/images/latest`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch latest image for application #${appId}`);
    return res.json();
  },

  async syncApplicationImage(appId: number): Promise<ContainerImageData> {
    const res = await fetch(`${API_BASE}/applications/${appId}/images/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to sync container image for application #${appId}`);
    return res.json();
  },

  async getKubernetesStatus(): Promise<KubernetesClusterStatus> {
    const res = await fetch(`${API_BASE}/integrations/kubernetes/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch Kubernetes cluster status`);
    return res.json();
  },

  async getApplicationDeployment(appId: number): Promise<KubernetesDeployment> {
    const res = await fetch(`${API_BASE}/applications/${appId}/deployment`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch deployment' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to fetch deployment`);
    }
    return res.json();
  },

  async deployApplication(
    appId: number,
    data?: { image_tag?: string; environment?: string; replicas?: number; port?: number }
  ): Promise<KubernetesDeployment> {
    const res = await fetch(`${API_BASE}/applications/${appId}/deploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to deploy application' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to deploy application`);
    }
    return res.json();
  },

  async redeployApplication(
    appId: number,
    data?: { image_tag?: string; replicas?: number }
  ): Promise<KubernetesDeployment> {
    const res = await fetch(`${API_BASE}/applications/${appId}/deployment/redeploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to redeploy application' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to redeploy application`);
    }
    return res.json();
  },

  async stopApplicationDeployment(appId: number): Promise<KubernetesDeployment> {
    const res = await fetch(`${API_BASE}/applications/${appId}/deployment/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to stop deployment' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to stop deployment`);
    }
    return res.json();
  },

  async getTerraformStatus(): Promise<TerraformStatus> {
    const res = await fetch(`${API_BASE}/infrastructure/terraform`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch Terraform status`);
    return res.json();
  },

  async planTerraform(environment = 'development'): Promise<TerraformPlanResponse> {
    const res = await fetch(`${API_BASE}/infrastructure/terraform/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ environment }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to generate Terraform plan' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to generate Terraform plan`);
    }
    return res.json();
  },

  async applyTerraform(environment = 'development', runId?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/infrastructure/terraform/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ environment, run_id: runId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to apply Terraform infrastructure' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to apply Terraform infrastructure`);
    }
    return res.json();
  },

  async getTerraformRuns(): Promise<TerraformRun[]> {
    const res = await fetch(`${API_BASE}/infrastructure/terraform/runs`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch Terraform runs`);
    return res.json();
  },

  // Phase 8: Ansible Automation
  async getAnsiblePlaybooks(): Promise<AnsiblePlaybook[]> {
    const res = await fetch(`${API_BASE}/ansible/playbooks`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch playbooks`);
    return res.json();
  },

  async createAnsibleExecution(req: CreateAnsibleExecutionRequest): Promise<AnsibleExecution> {
    const res = await fetch(`${API_BASE}/ansible/executions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create Ansible execution' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to execute playbook`);
    }
    return res.json();
  },

  async getAnsibleExecution(executionId: number): Promise<AnsibleExecution> {
    const res = await fetch(`${API_BASE}/ansible/executions/${executionId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch execution #${executionId}`);
    return res.json();
  },

  async listAnsibleExecutions(params?: { application_id?: number; environment_id?: string; status?: string }): Promise<AnsibleExecution[]> {
    const query = new URLSearchParams();
    if (params?.application_id) query.append('application_id', params.application_id.toString());
    if (params?.environment_id) query.append('environment_id', params.environment_id);
    if (params?.status) query.append('status', params.status);

    const res = await fetch(`${API_BASE}/ansible/executions?${query.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch Ansible executions`);
    return res.json();
  },

  async retryAnsibleExecution(executionId: number): Promise<AnsibleExecution> {
    const res = await fetch(`${API_BASE}/ansible/executions/${executionId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to retry execution' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to retry execution #${executionId}`);
    }
    return res.json();
  },

  async getSystemHealth(): Promise<SystemHealthData> {
    const res = await fetch(`${API_BASE}/monitoring/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch system health`);
    return res.json();
  },

  async getMetricsSummary(): Promise<MetricsSummaryData> {
    const res = await fetch(`${API_BASE}/monitoring/metrics/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch metrics summary`);
    return res.json();
  },

  async getMonitoredServices(): Promise<MonitoredService[]> {
    const res = await fetch(`${API_BASE}/monitoring/services`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch monitored services`);
    return res.json();
  },

  async getAlertRules(): Promise<AlertRule[]> {
    const res = await fetch(`${API_BASE}/monitoring/alerts`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch alert rules`);
    return res.json();
  },

  async getScrapeTargets(): Promise<ScrapeTarget[]> {
    const res = await fetch(`${API_BASE}/monitoring/targets`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch scrape targets`);
    return res.json();
  },

  // Phase 10: GitOps & Argo CD
  async getGitOpsClusterStatus(): Promise<ArgoCDClusterStatus> {
    const res = await fetch(`${API_BASE}/gitops/cluster`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch Argo CD cluster status`);
    return res.json();
  },

  async listGitOpsApplications(): Promise<GitOpsApplication[]> {
    const res = await fetch(`${API_BASE}/gitops/applications`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch GitOps applications`);
    return res.json();
  },

  async getGitOpsApplication(applicationId: number): Promise<GitOpsApplication> {
    const res = await fetch(`${API_BASE}/gitops/applications/${applicationId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch GitOps application #${applicationId}`);
    return res.json();
  },

  async enableGitOps(applicationId: number, req?: EnableGitOpsRequest): Promise<GitOpsOperation> {
    const res = await fetch(`${API_BASE}/gitops/applications/${applicationId}/enable`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req || {}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to enable GitOps' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to enable GitOps`);
    }
    return res.json();
  },

  async syncGitOpsApplication(applicationId: number, revision?: string): Promise<GitOpsOperation> {
    const res = await fetch(`${API_BASE}/gitops/applications/${applicationId}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to trigger GitOps sync' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to trigger GitOps sync`);
    }
    return res.json();
  },

  async refreshGitOpsApplication(applicationId: number): Promise<GitOpsOperation> {
    const res = await fetch(`${API_BASE}/gitops/applications/${applicationId}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to trigger GitOps refresh' }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to trigger GitOps refresh`);
    }
    return res.json();
  },

  async getGitOpsOperation(operationId: number): Promise<GitOpsOperation> {
    const res = await fetch(`${API_BASE}/gitops/operations/${operationId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch GitOps operation #${operationId}`);
    return res.json();
  },

  // ===========================================================================
  // Phase 11: Self-Healing & Remediation API
  // ===========================================================================
  async getApplicationRemediation(applicationId: number | string): Promise<ApplicationRemediationOverview> {
    const res = await fetch(`${API_BASE}/applications/${applicationId}/remediation`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch remediation summary for application ${applicationId}`);
    return res.json();
  },

  async listRemediationEvents(applicationId?: number): Promise<RemediationEvent[]> {
    const url = applicationId
      ? `${API_BASE}/remediation/events?application_id=${applicationId}`
      : `${API_BASE}/remediation/events`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch remediation events`);
    return res.json();
  },

  async retryRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const res = await fetch(`${API_BASE}/remediation/events/${eventId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to retry remediation event #${eventId}`);
    return res.json();
  },

  async approveRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const res = await fetch(`${API_BASE}/remediation/events/${eventId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to approve remediation event #${eventId}`);
    return res.json();
  },

  async cancelRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const res = await fetch(`${API_BASE}/remediation/events/${eventId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to cancel remediation event #${eventId}`);
    return res.json();
  },

  async triggerHealthScan(): Promise<{ status: string; events_detected_count: number }> {
    const res = await fetch(`${API_BASE}/remediation/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to trigger health scan`);
    return res.json();
  },

  async listRemediationPolicies(): Promise<RemediationPolicy[]> {
    const res = await fetch(`${API_BASE}/remediation/policies`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch remediation policies`);
    return res.json();
  }
};


