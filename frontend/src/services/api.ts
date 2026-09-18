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
  GitHubStatusResponse
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

  async getActivity(): Promise<Activity[]> {
    const res = await fetch(`${API_BASE}/activity`);
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
  }
};
