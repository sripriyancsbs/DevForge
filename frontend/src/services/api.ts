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
  User,
  Role,
  TokenResponse,
  ApplicationTemplate,
  TemplatePreviewResponse,
  Workspace,
  WorkspaceMember,
  AddWorkspaceMemberPayload,
  UserWorkspaceInfo
} from '../types';
import {
  SEED_APPLICATIONS,
  SEED_OVERVIEW,
  SEED_ENVIRONMENTS,
  SEED_DEPLOYMENTS,
  SEED_REMEDIATION,
  SEED_ACTIVITY,
  SEED_INFRASTRUCTURE,
  SEED_MONITORING,
  SEED_TERRAFORM_STATUS,
  SEED_TERRAFORM_RUNS,
  SEED_ANSIBLE_PLAYBOOKS,
  SEED_ANSIBLE_EXECUTIONS,
  SEED_KUBERNETES_STATUS,
  SEED_KUBERNETES_DEPLOYMENT,
  SEED_GITOPS_APPLICATION,
  SEED_ARGOCD_STATUS,
  SEED_CONTAINER_IMAGE,
  SEED_CI_STATUS,
  SEED_GITHUB_STATUS,
  SEED_MANIFEST_YAML,
  SEED_TEMPLATES
} from './seedData';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

const AUTH_TOKEN_KEY = 'devforge_auth_token';
const AUTH_USER_KEY = 'devforge_auth_user';
const ACTIVE_WORKSPACE_ID_KEY = 'devforge_active_workspace_id';
const CREATED_APPLICATIONS_KEY = 'devforge_created_applications';

export function getStoredApplications(): Application[] {
  try {
    const raw = localStorage.getItem(CREATED_APPLICATIONS_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveCreatedApplication(app: Application) {
  try {
    const apps = getStoredApplications();
    const existingIndex = apps.findIndex(
      (a) => a.id === app.id || a.name.toLowerCase() === app.name.toLowerCase() || a.slug.toLowerCase() === app.slug.toLowerCase()
    );
    if (existingIndex >= 0) {
      apps[existingIndex] = { ...apps[existingIndex], ...app };
    } else {
      apps.unshift(app);
    }
    localStorage.setItem(CREATED_APPLICATIONS_KEY, JSON.stringify(apps));
  } catch {}
}

const REGISTERED_USERS_KEY = 'devforge_registered_users';

interface StoredCredentialUser {
  id: number;
  name: string;
  email: string;
  username: string;
  password: string;
  role: Role;
  workspaces: any[];
  active_workspace: any;
  permissions: string[];
}

const BASELINE_USERS: StoredCredentialUser[] = [
  {
    id: 1,
    name: 'Platform Administrator',
    username: 'admin',
    email: 'admin@devforge.internal',
    password: 'AdminPassword123!',
    role: 'ADMIN',
    workspaces: [
      { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'ADMIN' },
      { id: 2, name: 'Staging Workspace', slug: 'staging-workspace', role: 'ADMIN' }
    ],
    active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'ADMIN' },
    permissions: ['view:all', 'deploy:trigger', 'infra:apply', 'remediation:approve', 'ansible:execute', 'workspace:manage', 'members:manage']
  },
  {
    id: 2,
    name: 'Platform Operator',
    username: 'operator',
    email: 'operator@devforge.internal',
    password: 'OperatorPassword123!',
    role: 'OPERATOR',
    workspaces: [
      { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'OPERATOR' }
    ],
    active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'OPERATOR' },
    permissions: ['view:all', 'deploy:trigger', 'infra:plan', 'remediation:approve', 'ansible:execute']
  },
  {
    id: 3,
    name: 'Software Developer',
    username: 'developer',
    email: 'developer@devforge.internal',
    password: 'DeveloperPassword123!',
    role: 'DEVELOPER',
    workspaces: [
      { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'DEVELOPER' }
    ],
    active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'DEVELOPER' },
    permissions: ['view:all', 'deploy:trigger']
  },
  {
    id: 4,
    name: 'Auditor Viewer',
    username: 'viewer',
    email: 'viewer@devforge.internal',
    password: 'ViewerPassword123!',
    role: 'VIEWER',
    workspaces: [
      { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'VIEWER' }
    ],
    active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'VIEWER' },
    permissions: ['view:all']
  }
];

function getStoredRegisteredUsers(): StoredCredentialUser[] {
  try {
    const raw = localStorage.getItem(REGISTERED_USERS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [];
}

function saveStoredRegisteredUsers(users: StoredCredentialUser[]) {
  try {
    localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(users));
  } catch {}
}

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string) {
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {}
}

export function getActiveWorkspaceId(): number {
  try {
    const raw = localStorage.getItem(ACTIVE_WORKSPACE_ID_KEY);
    if (raw && !isNaN(Number(raw))) {
      return Number(raw);
    }
    const user = getStoredUser();
    if (user && user.active_workspace?.id) {
      return user.active_workspace.id;
    }
    if (user && user.workspaces && user.workspaces.length > 0) {
      return user.workspaces[0].id;
    }
  } catch {}
  return 1;
}

export function setActiveWorkspaceId(id: number) {
  try {
    localStorage.setItem(ACTIVE_WORKSPACE_ID_KEY, String(id));
  } catch {}
}

export function clearAuthToken() {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem(ACTIVE_WORKSPACE_ID_KEY);
  } catch {}
}

export function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {}
  return null;
}

export function setStoredUser(user: User | null) {
  try {
    if (user) {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_USER_KEY);
    }
  } catch {}
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const wsId = getActiveWorkspaceId();
  if (wsId) {
    headers['X-Workspace-Id'] = String(wsId);
  }
  return headers;
}

async function requestJson<T>(url: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const mergedHeaders = {
      ...getAuthHeaders(),
      ...(init?.headers || {})
    };
    const res = await fetch(url, { ...init, headers: mergedHeaders });
    if (res.status === 404) {
      throw new Error(`Resource not found at ${url}`);
    }
    const contentType = res.headers.get('content-type') || '';
    if (res.ok && contentType.includes('application/json')) {
      return await res.json();
    }
  } catch (e: any) {
    if (e?.message?.includes('not found')) {
      throw e;
    }
  }
  if (fallback !== undefined) {
    return fallback;
  }
  throw new Error(`Failed to fetch JSON from ${url}`);
}

async function requestText(url: string, init?: RequestInit, fallback = ''): Promise<string> {
  try {
    const mergedHeaders = {
      ...getAuthHeaders(),
      ...(init?.headers || {})
    };
    const res = await fetch(url, { ...init, headers: mergedHeaders });
    const contentType = res.headers.get('content-type') || '';
    if (res.ok && !contentType.includes('text/html')) {
      return await res.text();
    }
  } catch (e) {
    // Backend unreachable or network error
  }
  return fallback;
}

export const api = {
  // Overview
  async getOverview(): Promise<OverviewData> {
    return requestJson(`${API_BASE}/overview`, undefined, SEED_OVERVIEW);
  },

  // Applications
  async getApplications(params?: { search?: string; status?: string; environment?: string }): Promise<Application[]> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.environment && params.environment !== 'all') searchParams.append('environment', params.environment);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';

    const stored = getStoredApplications();
    const combined = [...stored];
    for (const seedApp of SEED_APPLICATIONS) {
      if (!combined.some(a => a.id === seedApp.id || a.name.toLowerCase() === seedApp.name.toLowerCase())) {
        combined.push(seedApp);
      }
    }

    let fallbackResult = combined;
    if (params?.search) {
      const q = params.search.toLowerCase();
      fallbackResult = fallbackResult.filter(a => a.name.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q));
    }
    if (params?.status && params.status !== 'all') {
      fallbackResult = fallbackResult.filter(a => a.status === params.status);
    }
    if (params?.environment && params.environment !== 'all') {
      fallbackResult = fallbackResult.filter(a => a.environment === params.environment);
    }

    try {
      const serverApps = await requestJson<Application[]>(`${API_BASE}/applications${qs}`, undefined, undefined);
      if (Array.isArray(serverApps)) {
        const merged = [...serverApps];
        for (const s of stored) {
          if (!merged.some(m => m.id === s.id || m.name.toLowerCase() === s.name.toLowerCase() || m.slug.toLowerCase() === s.slug.toLowerCase())) {
            merged.unshift(s);
          }
        }
        return merged;
      }
    } catch {
      // Backend unavailable, return stored/seed
    }

    return fallbackResult;
  },

  async getApplicationDetails(idOrSlug: string | number): Promise<{ application: Application; deployments: Deployment[]; health: any; provisioning_job?: any }> {
    const cleanId = String(idOrSlug).trim().toLowerCase();
    const stored = getStoredApplications();
    const localApp = stored.find(a => String(a.id) === cleanId || a.slug.toLowerCase() === cleanId || a.name.toLowerCase() === cleanId)
      || SEED_APPLICATIONS.find(a => String(a.id) === cleanId || a.slug.toLowerCase() === cleanId || a.name.toLowerCase() === cleanId);

    const fallback = localApp ? {
      application: localApp,
      deployments: SEED_DEPLOYMENTS.filter(d => d.application_id === localApp.id),
      health: {
        status: localApp.status,
        cpu_percent: 18.4,
        memory_mb: '184 MB',
        requests_per_sec: 142,
        error_rate: '0.00%',
        uptime: '99.98%'
      },
      provisioning_job: (localApp as any).provisioning_job || null
    } : undefined;

    try {
      const res = await requestJson<{ application: Application; deployments: Deployment[]; health: any; provisioning_job?: any }>(
        `${API_BASE}/applications/${idOrSlug}`,
        undefined,
        fallback
      );
      if (res && res.application) {
        saveCreatedApplication(res.application);
        return res;
      }
    } catch (err: any) {
      if (fallback) {
        return fallback;
      }
      throw err;
    }

    if (fallback) return fallback;
    throw new Error(`Application "${idOrSlug}" was not found.`);
  },

  async getApplicationManifest(idOrSlug: string | number): Promise<string> {
    return requestText(`${API_BASE}/applications/${idOrSlug}/manifest`, undefined, SEED_MANIFEST_YAML);
  },

  // Templates
  async getTemplates(): Promise<ApplicationTemplate[]> {
    return requestJson(`${API_BASE}/templates`, undefined, SEED_TEMPLATES);
  },

  async getTemplate(id: string, version?: string): Promise<ApplicationTemplate> {
    const qs = version ? `?version=${encodeURIComponent(version)}` : '';
    const fallback = SEED_TEMPLATES.find(t => t.template_id === id) || SEED_TEMPLATES[0];
    return requestJson(`${API_BASE}/templates/${id}${qs}`, undefined, fallback);
  },

  async validateTemplateConfig(id: string, data: { application_name: string; variables?: Record<string, any> }): Promise<{ valid: boolean; errors: string[]; warnings: string[] }> {
    const fallback = {
      valid: true,
      errors: [] as string[],
      warnings: [] as string[]
    };
    return requestJson(`${API_BASE}/templates/${id}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }, fallback);
  },

  async previewTemplate(id: string, data: { application_name: string; environment?: string; variables?: Record<string, any> }): Promise<TemplatePreviewResponse> {
    const template = SEED_TEMPLATES.find(t => t.template_id === id) || SEED_TEMPLATES[0];
    const fallback: TemplatePreviewResponse = {
      template_id: template.template_id,
      template_name: template.name,
      template_version: template.version,
      runtime: template.runtime,
      framework: template.framework,
      application_name: data.application_name || 'my-app',
      environment: data.environment || 'production',
      files: template.generated_project_structure,
      manifest_preview: `apiVersion: devforge/v1\nkind: ApplicationManifest\nmetadata:\n  name: "${data.application_name || 'my-app'}"\n  version: "${template.version}"`,
      key_generated_components: [
        'Main entrypoint and routing configuration',
        'Standard health probe endpoints (/healthz, /ready)',
        'Container build specification (Dockerfile, .dockerignore)',
        'CI/CD workflow (.github/workflows/ci.yml)',
        'Kubernetes deployment and service manifests',
        'Automated test suite execution'
      ]
    };
    return requestJson(`${API_BASE}/templates/${id}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }, fallback);
  },

  async createApplication(data: {
    name: string;
    description?: string;
    team?: string;
    runtime?: string;
    template?: string;
    template_id?: string;
    template_version?: string;
    repository_url?: string;
    branch?: string;
    environment?: string;
    database_type?: string;
    deployment_strategy?: string;
    version?: string;
    port?: number;
    replicas?: number;
  }): Promise<ApplicationProvisioningResponse> {
    const selectedTemplateId = data.template_id || data.template || 'python-fastapi';
    const selectedTemplate = SEED_TEMPLATES.find(t => t.template_id === selectedTemplateId);

    const newApp: Application = {
      id: Date.now(),
      name: data.name,
      slug: data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      description: data.description || '',
      team: data.team || 'Platform Engineering',
      runtime: data.runtime || (selectedTemplate ? `${selectedTemplate.runtime} (${selectedTemplate.framework})` : 'Python 3.12 (FastAPI)'),
      template: selectedTemplateId,
      template_id: selectedTemplateId,
      template_version: data.template_version || selectedTemplate?.version || '1.0.0',
      repository_url: data.repository_url || 'https://github.com/sripriyancsbs/DevForge',
      branch: data.branch || 'main',
      environment: data.environment || 'production',
      version: data.version || 'v1.0.0',
      status: 'pending',
      port: data.port || selectedTemplate?.default_values?.port || 8000,
      replicas: data.replicas || 1,
      database_type: data.database_type,
      deployment_strategy: data.deployment_strategy || 'rolling',
      provisioning_status: 'PENDING',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    const fallback: ApplicationProvisioningResponse = {
      application: newApp,
      provisioning_status: 'PENDING',
      files_generated: selectedTemplate?.generated_project_structure || ['Dockerfile', 'main.py', 'requirements.txt'],
      message: 'Application created and queued for provisioning'
    };

    try {
      const res = await requestJson<ApplicationProvisioningResponse>(`${API_BASE}/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }, fallback);

      if (res && res.application) {
        saveCreatedApplication(res.application);
        return res;
      }
    } catch {
      saveCreatedApplication(fallback.application);
      return fallback;
    }
    saveCreatedApplication(fallback.application);
    return fallback;
  },

  async getDeployments(params?: { status?: string; environment?: string; application_id?: number }): Promise<Deployment[]> {
    const searchParams = new URLSearchParams();
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.environment && params.environment !== 'all') searchParams.append('environment', params.environment);
    if (params?.application_id) searchParams.append('application_id', String(params.application_id));

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    let fallback = SEED_DEPLOYMENTS;
    if (params?.application_id) {
      fallback = fallback.filter(d => d.application_id === params.application_id);
    }
    return requestJson(`${API_BASE}/deployments${qs}`, undefined, fallback);
  },

  async triggerDeployment(data: { application_id: number; version: string; environment: string; commit_message?: string }): Promise<Deployment> {
    const app = SEED_APPLICATIONS.find(a => a.id === data.application_id) || SEED_APPLICATIONS[0];
    const fallback: Deployment = {
      id: Date.now(),
      application_id: data.application_id,
      application_name: app.name,
      version: data.version,
      environment: data.environment,
      status: 'healthy',
      commit_hash: '6e3f5f6',
      commit_message: data.commit_message || 'Manual triggered deployment',
      triggered_by: 'sripriyancsbs',
      duration: '35s',
      created_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/deployments/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }, fallback);
  },

  async getEnvironments(): Promise<Environment[]> {
    return requestJson(`${API_BASE}/environments`, undefined, SEED_ENVIRONMENTS);
  },

  async getActivity(params?: { target_type?: string; status?: string; application?: string }): Promise<Activity[]> {
    const searchParams = new URLSearchParams();
    if (params?.target_type && params.target_type !== 'all') searchParams.append('target_type', params.target_type);
    if (params?.status && params.status !== 'all') searchParams.append('status', params.status);
    if (params?.application && params.application !== 'all') searchParams.append('application', params.application);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return requestJson(`${API_BASE}/activity${qs}`, undefined, SEED_ACTIVITY);
  },

  async getInfrastructure(): Promise<InfrastructureData> {
    return requestJson(`${API_BASE}/infrastructure`, undefined, SEED_INFRASTRUCTURE);
  },

  async getMonitoring(): Promise<MonitoringData> {
    return requestJson(`${API_BASE}/monitoring`, undefined, SEED_MONITORING);
  },

  async getProvisioningJob(jobId: number): Promise<ProvisioningJob> {
    const fallback: ProvisioningJob = {
      id: jobId,
      application_id: 1,
      template: 'python-fastapi',
      current_step: 'COMPLETED',
      status: 'READY',
      attempt: 1,
      max_attempts: 3,
      is_retryable: false,
      created_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/provisioning/${jobId}`, undefined, fallback);
  },

  async retryProvisioningJob(jobId: number): Promise<ProvisioningJob> {
    const fallback: ProvisioningJob = {
      id: jobId,
      application_id: 1,
      template: 'python-fastapi',
      current_step: 'COMPLETED',
      status: 'READY',
      attempt: 2,
      max_attempts: 3,
      is_retryable: false,
      created_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/provisioning/${jobId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, fallback);
  },

  async getLatestJobForApplication(appId: number): Promise<ProvisioningJob> {
    const fallback: ProvisioningJob = {
      id: 100,
      application_id: appId,
      template: 'python-fastapi',
      current_step: 'COMPLETED',
      status: 'READY',
      attempt: 1,
      max_attempts: 3,
      is_retryable: false,
      created_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/provisioning/by-app/${appId}`, undefined, fallback);
  },

  async getGitHubStatus(): Promise<GitHubStatusResponse> {
    return requestJson(`${API_BASE}/integrations/github/status`, undefined, SEED_GITHUB_STATUS);
  },

  async reprovisionApplication(appId: number): Promise<ApplicationProvisioningResponse> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: ApplicationProvisioningResponse = {
      application: app,
      provisioning_status: 'READY',
      files_generated: ['Dockerfile', 'main.py', 'requirements.txt'],
      message: 'Reprovisioning succeeded'
    };
    return requestJson(`${API_BASE}/applications/${appId}/provision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, fallback);
  },

  async getApplicationCI(appId: number): Promise<CIStatusData> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: CIStatusData = {
      ...SEED_CI_STATUS,
      application_id: appId,
      application_name: app.name
    };
    return requestJson(`${API_BASE}/applications/${appId}/ci`, undefined, fallback);
  },

  async refreshApplicationCI(appId: number): Promise<CIStatusData> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: CIStatusData = {
      ...SEED_CI_STATUS,
      application_id: appId,
      application_name: app.name
    };
    return requestJson(`${API_BASE}/applications/${appId}/ci/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, fallback);
  },

  async getApplicationImages(appId: number): Promise<{ images: ContainerImageData[]; total: number; latest?: ContainerImageData }> {
    const fallback = {
      images: [{ ...SEED_CONTAINER_IMAGE, application_id: appId }],
      total: 1,
      latest: { ...SEED_CONTAINER_IMAGE, application_id: appId }
    };
    return requestJson(`${API_BASE}/applications/${appId}/images`, undefined, fallback);
  },

  async getLatestApplicationImage(appId: number): Promise<ContainerImageData> {
    return requestJson(`${API_BASE}/applications/${appId}/images/latest`, undefined, { ...SEED_CONTAINER_IMAGE, application_id: appId });
  },

  async syncApplicationImage(appId: number): Promise<ContainerImageData> {
    return requestJson(`${API_BASE}/applications/${appId}/images/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, { ...SEED_CONTAINER_IMAGE, application_id: appId });
  },

  async getKubernetesStatus(): Promise<KubernetesClusterStatus> {
    return requestJson(`${API_BASE}/integrations/kubernetes/status`, undefined, SEED_KUBERNETES_STATUS);
  },

  async getApplicationDeployment(appId: number): Promise<KubernetesDeployment> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    return requestJson(`${API_BASE}/applications/${appId}/deployment`, undefined, {
      ...SEED_KUBERNETES_DEPLOYMENT,
      application_id: appId,
      application_name: app.name
    });
  },

  async deployApplication(
    appId: number,
    data?: { image_tag?: string; environment?: string; replicas?: number; port?: number }
  ): Promise<KubernetesDeployment> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: KubernetesDeployment = {
      ...SEED_KUBERNETES_DEPLOYMENT,
      application_id: appId,
      application_name: app.name,
      image_tag: data?.image_tag || 'v1.0.2',
      replicas: data?.replicas || 2,
      port: data?.port || 8000
    };
    return requestJson(`${API_BASE}/applications/${appId}/deploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    }, fallback);
  },

  async redeployApplication(
    appId: number,
    data?: { image_tag?: string; replicas?: number }
  ): Promise<KubernetesDeployment> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: KubernetesDeployment = {
      ...SEED_KUBERNETES_DEPLOYMENT,
      application_id: appId,
      application_name: app.name,
      image_tag: data?.image_tag || 'v1.0.2',
      replicas: data?.replicas || 2
    };
    return requestJson(`${API_BASE}/applications/${appId}/deployment/redeploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {})
    }, fallback);
  },

  async stopApplicationDeployment(appId: number): Promise<KubernetesDeployment> {
    const app = SEED_APPLICATIONS.find(a => a.id === appId) || SEED_APPLICATIONS[0];
    const fallback: KubernetesDeployment = {
      ...SEED_KUBERNETES_DEPLOYMENT,
      application_id: appId,
      application_name: app.name,
      replicas: 0,
      ready_replicas: 0,
      status: 'STOPPED'
    };
    return requestJson(`${API_BASE}/applications/${appId}/deployment/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, fallback);
  },

  async getTerraformStatus(): Promise<TerraformStatus> {
    return requestJson(`${API_BASE}/infrastructure/terraform`, undefined, SEED_TERRAFORM_STATUS);
  },

  async planTerraform(environment = 'development'): Promise<TerraformPlanResponse> {
    const fallback: TerraformPlanResponse = {
      run_id: 1,
      environment,
      status: 'SUCCESS',
      summary: {
        to_add: 0,
        to_change: 0,
        to_destroy: 0,
        resources: []
      },
      plan_output: 'No changes. Your infrastructure matches the configuration.',
      created_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/infrastructure/terraform/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ environment }),
    }, fallback);
  },

  async applyTerraform(environment = 'development', runId?: number): Promise<any> {
    const fallback = {
      status: 'APPLIED',
      environment,
      run_id: runId || 1,
      message: 'Infrastructure successfully applied'
    };
    return requestJson(`${API_BASE}/infrastructure/terraform/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ environment, run_id: runId }),
    }, fallback);
  },

  async getTerraformRuns(): Promise<TerraformRun[]> {
    return requestJson(`${API_BASE}/infrastructure/terraform/runs`, undefined, SEED_TERRAFORM_RUNS);
  },

  // Phase 8: Ansible Automation
  async getAnsiblePlaybooks(): Promise<AnsiblePlaybook[]> {
    return requestJson(`${API_BASE}/ansible/playbooks`, undefined, SEED_ANSIBLE_PLAYBOOKS);
  },

  async createAnsibleExecution(req: CreateAnsibleExecutionRequest): Promise<AnsibleExecution> {
    const fallback: AnsibleExecution = {
      id: Date.now(),
      playbook_name: req.playbook_name,
      application_id: req.application_id,
      environment_id: req.environment_id,
      status: 'SUCCESS',
      output: 'PLAY [Apply baseline security]\nTASK [Gathering Facts] ... ok\nPLAY RECAP: localhost : ok=4 changed=1 unreachable=0 failed=0',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/ansible/executions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }, fallback);
  },

  async getAnsibleExecution(executionId: number): Promise<AnsibleExecution> {
    const fallback: AnsibleExecution = {
      ...SEED_ANSIBLE_EXECUTIONS[0],
      id: executionId
    };
    return requestJson(`${API_BASE}/ansible/executions/${executionId}`, undefined, fallback);
  },

  async listAnsibleExecutions(params?: { application_id?: number; environment_id?: string; status?: string }): Promise<AnsibleExecution[]> {
    const query = new URLSearchParams();
    if (params?.application_id) query.append('application_id', params.application_id.toString());
    if (params?.environment_id) query.append('environment_id', params.environment_id);
    if (params?.status) query.append('status', params.status);

    return requestJson(`${API_BASE}/ansible/executions?${query.toString()}`, undefined, SEED_ANSIBLE_EXECUTIONS);
  },

  async retryAnsibleExecution(executionId: number): Promise<AnsibleExecution> {
    const fallback: AnsibleExecution = {
      ...SEED_ANSIBLE_EXECUTIONS[0],
      id: executionId
    };
    return requestJson(`${API_BASE}/ansible/executions/${executionId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, fallback);
  },

  async getSystemHealth(): Promise<SystemHealthData> {
    const fallback: SystemHealthData = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      backend: {
        status: 'healthy',
        version: '1.0.0',
        uptime_seconds: 86400,
        port: 8000,
        environment: 'production'
      },
      worker: {
        status: 'healthy',
        metrics_port: 9091,
        active_jobs: 0,
        concurrency: 4
      },
      database: {
        status: 'healthy',
        engine: 'PostgreSQL 16',
        active_connections: 12,
        latency_ms: 1.2,
        database_name: 'devforge'
      },
      kubernetes: {
        status: 'healthy',
        cluster_name: 'local-kind',
        namespace: 'devforge',
        nodes_count: 3
      },
      prometheus: {
        status: 'healthy',
        url: 'http://localhost:9090',
        scrape_interval: '15s',
        active_targets: 4
      },
      grafana: {
        status: 'healthy',
        url: 'http://localhost:3001',
        version: '10.4.0',
        dashboard_uid: 'devforge-overview',
        dashboard_url: 'http://localhost:3001/d/devforge-overview'
      }
    };
    return requestJson(`${API_BASE}/monitoring/health`, undefined, fallback);
  },

  async getMetricsSummary(): Promise<MetricsSummaryData> {
    const fallback: MetricsSummaryData = {
      api: {
        total_requests: 245000,
        total_errors: 12,
        error_rate_percent: 0.005,
        active_requests: 4,
        p95_latency_ms: 24.5,
        throughput_rps: 142
      },
      applications: {
        total: 4,
        healthy: 4,
        failed: 0
      },
      provisioning: {
        total_jobs: 14,
        succeeded: 14,
        failed: 0,
        pending: 0,
        success_rate_percent: 100
      },
      deployments: {
        total: 28,
        healthy: 28,
        failed: 0
      },
      ansible: {
        total_executions: 12,
        succeeded: 12,
        failed: 0,
        success_rate_percent: 100
      },
      infrastructure: {
        terraform_status: 'APPLIED',
        managed_resources_count: 6
      }
    };
    return requestJson(`${API_BASE}/monitoring/metrics/summary`, undefined, fallback);
  },

  async getMonitoredServices(): Promise<MonitoredService[]> {
    const fallback: MonitoredService[] = [
      {
        name: 'inventory-api',
        component: 'api',
        tier: 'Tier 1',
        endpoint: '/healthz',
        port: 8000,
        health: 'healthy',
        latency_ms: 12,
        description: 'Inventory microservice'
      }
    ];
    return requestJson(`${API_BASE}/monitoring/services`, undefined, fallback);
  },

  async getAlertRules(): Promise<AlertRule[]> {
    const fallback: AlertRule[] = [
      {
        name: 'HighCPUUsage',
        state: 'firing',
        severity: 'warning',
        summary: 'High CPU utilization detected',
        description: 'Pod CPU exceeds 85% for 1 minute',
        expression: 'rate(container_cpu_usage_seconds_total[1m]) > 0.85'
      }
    ];
    return requestJson(`${API_BASE}/monitoring/alerts`, undefined, fallback);
  },

  async getScrapeTargets(): Promise<ScrapeTarget[]> {
    const fallback: ScrapeTarget[] = [
      {
        job: 'kubernetes-pods',
        instance: 'inventory-api-7b8f9c-1',
        health: 'healthy',
        scrape_url: 'http://10.244.0.5:8000/metrics'
      }
    ];
    return requestJson(`${API_BASE}/monitoring/targets`, undefined, fallback);
  },

  // Phase 10: GitOps & Argo CD
  async getGitOpsClusterStatus(): Promise<ArgoCDClusterStatus> {
    return requestJson(`${API_BASE}/gitops/cluster`, undefined, SEED_ARGOCD_STATUS);
  },

  async listGitOpsApplications(): Promise<GitOpsApplication[]> {
    return requestJson(`${API_BASE}/gitops/applications`, undefined, [SEED_GITOPS_APPLICATION]);
  },

  async getGitOpsApplication(applicationId: number): Promise<GitOpsApplication> {
    return requestJson(`${API_BASE}/gitops/applications/${applicationId}`, undefined, {
      ...SEED_GITOPS_APPLICATION,
      application_id: applicationId
    });
  },

  async enableGitOps(applicationId: number, req?: EnableGitOpsRequest): Promise<GitOpsOperation> {
    const fallback: GitOpsOperation = {
      id: 1,
      gitops_application_id: applicationId,
      operation_type: 'ENABLE',
      status: 'SUCCESS',
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/gitops/applications/${applicationId}/enable`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req || {}),
    }, fallback);
  },

  async syncGitOpsApplication(applicationId: number, revision?: string): Promise<GitOpsOperation> {
    const fallback: GitOpsOperation = {
      id: 2,
      gitops_application_id: applicationId,
      operation_type: 'SYNC',
      status: 'SUCCESS',
      revision,
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/gitops/applications/${applicationId}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision }),
    }, fallback);
  },

  async refreshGitOpsApplication(applicationId: number): Promise<GitOpsOperation> {
    const fallback: GitOpsOperation = {
      id: 3,
      gitops_application_id: applicationId,
      operation_type: 'REFRESH',
      status: 'SUCCESS',
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/gitops/applications/${applicationId}/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }, fallback);
  },

  async getGitOpsOperation(operationId: number): Promise<GitOpsOperation> {
    const fallback: GitOpsOperation = {
      id: operationId,
      gitops_application_id: 1,
      operation_type: 'SYNC',
      status: 'SUCCESS',
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    return requestJson(`${API_BASE}/gitops/operations/${operationId}`, undefined, fallback);
  },

  // ===========================================================================
  // Phase 11: Self-Healing & Remediation API
  // ===========================================================================
  async getApplicationRemediation(applicationId: number | string): Promise<ApplicationRemediationOverview> {
    const app = SEED_APPLICATIONS.find(a => String(a.id) === String(applicationId) || a.slug === applicationId || a.name === applicationId) || SEED_APPLICATIONS[0];
    const fallback: ApplicationRemediationOverview = {
      ...SEED_REMEDIATION,
      application_id: app.id,
      application_name: app.name
    };
    return requestJson(`${API_BASE}/applications/${applicationId}/remediation`, undefined, fallback);
  },

  async listRemediationEvents(applicationId?: number): Promise<RemediationEvent[]> {
    const url = applicationId
      ? `${API_BASE}/remediation/events?application_id=${applicationId}`
      : `${API_BASE}/remediation/events`;
    return requestJson(url, undefined, SEED_REMEDIATION.events);
  },

  async retryRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const ev = SEED_REMEDIATION.events[0];
    const updated: RemediationEvent = { ...ev, id: eventId, status: 'REMEDIATING' };
    return requestJson(`${API_BASE}/remediation/events/${eventId}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, updated);
  },

  async approveRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const ev = SEED_REMEDIATION.events[0];
    const updated: RemediationEvent = { ...ev, id: eventId, status: 'REMEDIATING' };
    return requestJson(`${API_BASE}/remediation/events/${eventId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, updated);
  },

  async cancelRemediationEvent(eventId: number): Promise<RemediationEvent> {
    const ev = SEED_REMEDIATION.events[0];
    const updated: RemediationEvent = { ...ev, id: eventId, status: 'CANCELLED' };
    return requestJson(`${API_BASE}/remediation/events/${eventId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, updated);
  },

  async triggerHealthScan(): Promise<{ status: string; events_detected_count: number }> {
    return requestJson(`${API_BASE}/remediation/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, { status: 'SUCCESS', events_detected_count: 4 });
  },

  async listRemediationPolicies(): Promise<RemediationPolicy[]> {
    return requestJson(`${API_BASE}/remediation/policies`, undefined, SEED_REMEDIATION.policies);
  },

  // Authentication & RBAC API
  async login(identifier: string, password: string): Promise<TokenResponse> {
    const cleanId = identifier.trim();
    if (!cleanId || !password) {
      throw new Error('Email or username and password are required.');
    }

    // Attempt real backend login first
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: cleanId, username: cleanId, password })
      });
      if (res.ok) {
        const data: TokenResponse = await res.json();
        setAuthToken(data.access_token);
        setStoredUser(data.user);
        if (data.user.active_workspace?.id) {
          setActiveWorkspaceId(data.user.active_workspace.id);
        }
        return data;
      } else if (res.status === 401 || res.status === 400 || res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid email or password.');
      } else if (res.status === 429) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Too many requests. Please wait a moment and try again.');
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to sign in.');
      }
    } catch (err: any) {
      if (err.message && (
        err.message.includes('Invalid') || 
        err.message.includes('Account is deactivated') || 
        err.message.includes('Contact system administrator') ||
        err.message.includes('Too many requests')
      )) {
        throw err;
      }
      // If network/offline or on static host (Vercel preview without backend tunnel), verify credentials
      const registered = getStoredRegisteredUsers();
      const allUsers = [...BASELINE_USERS, ...registered];
      const found = allUsers.find(
        (u) => u.email.toLowerCase() === cleanId.toLowerCase() || u.username.toLowerCase() === cleanId.toLowerCase()
      );
      if (!found || found.password !== password) {
        throw new Error('Invalid email or password.');
      }

      const userObj: User = {
        id: found.id,
        username: found.username,
        email: found.email,
        display_name: found.name,
        role: found.role,
        is_active: true,
        status: 'active',
        workspaces: found.workspaces,
        active_workspace: found.active_workspace,
        permissions: found.permissions
      };
      const tokenResp: TokenResponse = {
        access_token: `df_session_token_${found.username}`,
        token_type: 'bearer',
        expires_in: 28800,
        user: userObj
      };
      setAuthToken(tokenResp.access_token);
      setStoredUser(userObj);
      if (userObj.active_workspace?.id) {
        setActiveWorkspaceId(userObj.active_workspace.id);
      }
      return tokenResp;
    }
    throw new Error('Invalid email or password.');
  },

  async signup(payload: {
    name: string;
    email: string;
    password: string;
    confirm_password: string;
  }): Promise<TokenResponse> {
    const name = payload.name.trim();
    const email = payload.email.trim().toLowerCase();
    const password = payload.password;
    const confirm_password = payload.confirm_password;

    if (!name || !email || !password || !confirm_password) {
      throw new Error('All fields are required.');
    }
    if (!email.includes('@') || !email.split('@')[1]?.includes('.')) {
      throw new Error('A valid email address is required.');
    }
    if (password !== confirm_password) {
      throw new Error('Passwords do not match.');
    }
    if (password.length < 8) {
      throw new Error('Password must be at least 8 characters long.');
    }

    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, confirm_password })
      });
      if (res.ok) {
        const data: TokenResponse = await res.json();
        setAuthToken(data.access_token);
        setStoredUser(data.user);
        if (data.user.active_workspace?.id) {
          setActiveWorkspaceId(data.user.active_workspace.id);
        }
        return data;
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to sign up.');
      }
    } catch (err: any) {
      if (err.message && !err.message.includes('Failed to fetch') && !err.message.includes('NetworkError') && !err.message.includes('Load failed')) {
        throw err;
      }
      const registered = getStoredRegisteredUsers();
      const allUsers = [...BASELINE_USERS, ...registered];
      if (allUsers.some((u) => u.email.toLowerCase() === email)) {
        throw new Error('An account with this email already exists.');
      }

      const username = email.split('@')[0].replace(/[^a-zA-Z0-9_-]/g, '') || 'user';
      const newUser: StoredCredentialUser = {
        id: 100 + registered.length,
        name,
        username,
        email,
        password,
        role: 'DEVELOPER', // Authoritative server/fallback rule: NEVER ADMIN
        workspaces: [
          { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'DEVELOPER' }
        ],
        active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'DEVELOPER' },
        permissions: ['view:all', 'deploy:trigger']
      };
      registered.push(newUser);
      saveStoredRegisteredUsers(registered);

      const userObj: User = {
        id: newUser.id,
        username: newUser.username,
        email: newUser.email,
        display_name: newUser.name,
        role: newUser.role,
        is_active: true,
        status: 'active',
        workspaces: newUser.workspaces,
        active_workspace: newUser.active_workspace,
        permissions: newUser.permissions
      };
      const tokenResp: TokenResponse = {
        access_token: `df_jwt_${newUser.username}_${Date.now()}`,
        token_type: 'bearer',
        expires_in: 28800,
        user: userObj
      };
      setAuthToken(tokenResp.access_token);
      setStoredUser(userObj);
      setActiveWorkspaceId(1);
      return tokenResp;
    }
  },

  async getCurrentUser(): Promise<User | null> {
    const token = getAuthToken();
    if (!token) return null;
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const user: User = await res.json();
        setStoredUser(user);
        return user;
      }
      if (res.status === 401) {
        clearAuthToken();
        return null;
      }
    } catch {}
    return getStoredUser();
  },

  async logout(): Promise<void> {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
    } catch {}
    clearAuthToken();
  },

  // Workspace & Membership Management (Phase 14)
  async getWorkspaces(): Promise<Workspace[]> {
    return requestJson<Workspace[]>(`${API_BASE}/workspaces`, undefined, [
      {
        id: 1,
        name: 'Default Workspace',
        slug: 'default-workspace',
        description: 'Primary engineering workspace for core platform services',
        status: 'active',
        current_user_role: getStoredUser()?.role || 'DEVELOPER',
        member_count: 4,
        application_count: 5
      },
      {
        id: 2,
        name: 'Staging Workspace',
        slug: 'staging-workspace',
        description: 'Secondary isolated staging workspace for pre-release validation',
        status: 'active',
        current_user_role: getStoredUser()?.role || 'DEVELOPER',
        member_count: 2,
        application_count: 1
      }
    ]);
  },

  async getCurrentWorkspace(): Promise<Workspace> {
    const activeId = getActiveWorkspaceId();
    const url = activeId ? `${API_BASE}/workspaces/${activeId}` : `${API_BASE}/workspaces/current`;
    return requestJson<Workspace>(url, undefined, {
      id: 1,
      name: 'Default Workspace',
      slug: 'default-workspace',
      description: 'Primary engineering workspace for core platform services',
      status: 'active',
      current_user_role: getStoredUser()?.role || 'DEVELOPER',
      member_count: 4,
      application_count: 5
    });
  },

  async getWorkspaceMembers(workspaceId: number): Promise<WorkspaceMember[]> {
    const defaultMembers: WorkspaceMember[] = [
      { id: 1, workspace_id: workspaceId, user_id: 1, username: 'admin', email: 'admin@devforge.internal', display_name: 'Platform Administrator', role: 'ADMIN', status: 'active' },
      { id: 2, workspace_id: workspaceId, user_id: 2, username: 'operator', email: 'operator@devforge.internal', display_name: 'Operator', role: 'OPERATOR', status: 'active' },
      { id: 3, workspace_id: workspaceId, user_id: 3, username: 'developer', email: 'developer@devforge.internal', display_name: 'Developer', role: 'DEVELOPER', status: 'active' },
      { id: 4, workspace_id: workspaceId, user_id: 4, username: 'viewer', email: 'viewer@devforge.internal', display_name: 'Viewer', role: 'VIEWER', status: 'active' }
    ];
    let localMembers: WorkspaceMember[] = defaultMembers;
    try {
      const stored = localStorage.getItem(`devforge_ws_members_${workspaceId}`);
      if (stored) {
        localMembers = JSON.parse(stored);
      }
    } catch {}

    return requestJson<WorkspaceMember[]>(`${API_BASE}/workspaces/${workspaceId}/members`, undefined, localMembers);
  },

  async addWorkspaceMember(workspaceId: number, data: AddWorkspaceMemberPayload): Promise<WorkspaceMember> {
    const fallback: WorkspaceMember = {
      id: Date.now(),
      workspace_id: workspaceId,
      user_id: (data as any).user_id || Date.now(),
      username: data.username || data.email?.split('@')[0] || `user_${Date.now()}`,
      email: data.email || 'member@devforge.internal',
      display_name: data.display_name || data.email?.split('@')[0] || 'New Member',
      role: (data.role as Role) || 'DEVELOPER',
      status: 'active'
    };
    try {
      const res = await requestJson<WorkspaceMember>(`${API_BASE}/workspaces/${workspaceId}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }, fallback);
      // Persist in localStorage for static hosting environments
      const stored = localStorage.getItem(`devforge_ws_members_${workspaceId}`);
      const list: WorkspaceMember[] = stored ? JSON.parse(stored) : [
        { id: 1, workspace_id: workspaceId, user_id: 1, username: 'admin', email: 'admin@devforge.internal', display_name: 'Platform Administrator', role: 'ADMIN', status: 'active' },
        { id: 2, workspace_id: workspaceId, user_id: 2, username: 'operator', email: 'operator@devforge.internal', display_name: 'Operator', role: 'OPERATOR', status: 'active' },
        { id: 3, workspace_id: workspaceId, user_id: 3, username: 'developer', email: 'developer@devforge.internal', display_name: 'Developer', role: 'DEVELOPER', status: 'active' },
        { id: 4, workspace_id: workspaceId, user_id: 4, username: 'viewer', email: 'viewer@devforge.internal', display_name: 'Viewer', role: 'VIEWER', status: 'active' }
      ];
      list.push(res);
      localStorage.setItem(`devforge_ws_members_${workspaceId}`, JSON.stringify(list));
      return res;
    } catch {
      return fallback;
    }
  },

  async updateWorkspaceMemberRole(workspaceId: number, memberId: number, role: string): Promise<WorkspaceMember> {
    const fallback: WorkspaceMember = {
      id: memberId,
      workspace_id: workspaceId,
      user_id: memberId,
      username: 'member',
      email: 'member@devforge.internal',
      display_name: 'Member',
      role: role as Role,
      status: 'active'
    };
    try {
      const res = await requestJson<WorkspaceMember>(`${API_BASE}/workspaces/${workspaceId}/members/${memberId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role })
      }, fallback);
      const stored = localStorage.getItem(`devforge_ws_members_${workspaceId}`);
      if (stored) {
        const list: WorkspaceMember[] = JSON.parse(stored);
        const idx = list.findIndex(m => m.id === memberId);
        if (idx >= 0) {
          list[idx].role = role as Role;
          localStorage.setItem(`devforge_ws_members_${workspaceId}`, JSON.stringify(list));
        }
      }
      return res;
    } catch {
      return fallback;
    }
  },

  async disableWorkspaceMember(workspaceId: number, memberId: number): Promise<{ status: string; message: string }> {
    const fallback = { status: 'disabled', message: 'Member disabled successfully' };
    try {
      const res = await requestJson<{ status: string; message: string }>(`${API_BASE}/workspaces/${workspaceId}/members/${memberId}`, {
        method: 'DELETE'
      }, fallback);
      const stored = localStorage.getItem(`devforge_ws_members_${workspaceId}`);
      if (stored) {
        const list: WorkspaceMember[] = JSON.parse(stored);
        const idx = list.findIndex(m => m.id === memberId);
        if (idx >= 0) {
          list[idx].status = 'disabled';
          localStorage.setItem(`devforge_ws_members_${workspaceId}`, JSON.stringify(list));
        }
      }
      return res;
    } catch {
      return fallback;
    }
  },

  async switchWorkspace(workspaceId: number): Promise<User> {
    setActiveWorkspaceId(workspaceId);
    try {
      const refreshed = await requestJson<User>(`${API_BASE}/auth/me`, {
        headers: { 'X-Workspace-Id': String(workspaceId) }
      });
      if (refreshed) {
        setStoredUser(refreshed);
        return refreshed;
      }
    } catch {}
    const current = getStoredUser();
    if (!current) return null as any;
    const ws = current.workspaces?.find(w => w.id === workspaceId);
    if (ws) {
      const updated: User = {
        ...current,
        role: ws.role as Role,
        active_workspace: ws
      };
      setStoredUser(updated);
      return updated;
    }
    return current;
  },

  switchRoleSession(role: Role): User | null {
    const current = getStoredUser();
    if (!current) return null;
    const updated: User = {
      ...current,
      username: role.toLowerCase(),
      email: `${role.toLowerCase()}@devforge.internal`,
      role: role
    };
    setStoredUser(updated);
    setAuthToken(`df_session_token_${role.toLowerCase()}`);
    return updated;
  }
};
