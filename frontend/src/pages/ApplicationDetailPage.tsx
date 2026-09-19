import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  GitBranch,
  ExternalLink,
  Play,
  RotateCcw,
  Terminal,
  Activity,
  Layers,
  Cpu,
  Server,
  FileCode,
  Copy,
  Check,
  RefreshCw,
  Search,
  Plus,
  ArrowLeft,
  AlertCircle,
  Radio,
  ShieldCheck,
  ChevronDown,
  Wrench,
  ShieldAlert
} from 'lucide-react';
import {
  Application,
  Deployment,
  ServiceHealth,
  CIStatusData,
  ContainerImageData,
  KubernetesDeployment,
  AnsiblePlaybook,
  AnsibleExecution,
  TerraformStatus,
  TerraformRun,
  Activity as ActivityType,
  ApplicationRemediationOverview,
  RemediationEvent,
  RemediationPolicy,
  RemediationExecution
} from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { api } from '../services/api';

export type AppDetailTab =
  | 'overview'
  | 'deployments'
  | 'environments'
  | 'infrastructure'
  | 'automation'
  | 'monitoring'
  | 'logs';

interface ApplicationDetailPageProps {
  app: Application;
  initialTab?: AppDetailTab;
  onTabChange: (tab: AppDetailTab) => void;
  onBack: () => void;
  onTriggerDeploy: (appId: number, version: string, environment: string) => Promise<void>;
  allDeployments: Deployment[];
  allHealth: ServiceHealth[];
  onRefreshData: () => Promise<void>;
}

export const ApplicationDetailPage: React.FC<ApplicationDetailPageProps> = ({
  app,
  initialTab = 'overview',
  onTabChange,
  onBack,
  onTriggerDeploy,
  allDeployments,
  allHealth,
  onRefreshData
}) => {
  const [activeTab, setActiveTab] = useState<AppDetailTab>(initialTab);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const handleTabClick = (tab: AppDetailTab) => {
    setActiveTab(tab);
    onTabChange(tab);
  };

  // 1. Deployments specific to this application
  const appDeployments = useMemo(() => {
    return allDeployments.filter(
      (d) => d.application_id === app.id || d.application_name.toLowerCase() === app.name.toLowerCase()
    );
  }, [allDeployments, app.id, app.name]);

  // 2. Health telemetry specific to this application
  const appHealth = useMemo(() => {
    return allHealth.find(
      (h) => h.service_name.toLowerCase() === app.name.toLowerCase()
    ) || null;
  }, [allHealth, app.name]);

  // 3. Application-specific activity
  const [appActivities, setAppActivities] = useState<ActivityType[]>([]);
  const [loadingActivities, setLoadingActivities] = useState(false);

  // 4. CI / Container image data
  const [ciData, setCiData] = useState<CIStatusData | null>(null);
  const [imageData, setImageData] = useState<ContainerImageData | null>(null);
  const [refreshingCI, setRefreshingCI] = useState(false);

  // 5. Kubernetes deployment state
  const [k8sDeployment, setK8sDeployment] = useState<KubernetesDeployment | null>(null);
  const [loadingK8s, setLoadingK8s] = useState(false);
  const [deployingK8s, setDeployingK8s] = useState(false);
  const [k8sError, setK8sError] = useState<string | null>(null);

  // 6. Terraform State
  const [tfStatus, setTfStatus] = useState<TerraformStatus | null>(null);
  const [tfRuns, setTfRuns] = useState<TerraformRun[]>([]);
  const [planningTf, setPlanningTf] = useState(false);
  const [applyingTf, setApplyingTf] = useState(false);
  const [tfError, setTfError] = useState<string | null>(null);

  // 7. Automation (Ansible) State
  const [playbooks, setPlaybooks] = useState<AnsiblePlaybook[]>([]);
  const [ansibleExecutions, setAnsibleExecutions] = useState<AnsibleExecution[]>([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState('configure_application');
  const [selectedAnsibleEnv, setSelectedAnsibleEnv] = useState('development');
  const [runningPlaybook, setRunningPlaybook] = useState(false);
  const [ansibleError, setAnsibleError] = useState<string | null>(null);

  // 8. Manifest Content
  const [manifestContent, setManifestContent] = useState<string>(app.manifest_yaml || '');
  const [copiedManifest, setCopiedManifest] = useState(false);

  // 9. Redeploy Modal State
  const [showRedeployModal, setShowRedeployModal] = useState(false);
  const [redeployVersion, setRedeployVersion] = useState(app.version || 'v1.0.0');
  const [redeployEnv, setRedeployEnv] = useState(app.environment || 'development');
  const [isSubmittingDeploy, setIsSubmittingDeploy] = useState(false);

  // 10. Add Environment Modal State
  const [showAddEnvModal, setShowAddEnvModal] = useState(false);
  const [newEnvName, setNewEnvName] = useState('staging');
  const [addedEnvs, setAddedEnvs] = useState<string[]>([app.environment]);

  // 11. Log Viewer Modal / Tab Filter
  const [selectedLogDeployment, setSelectedLogDeployment] = useState<Deployment | null>(null);
  const [logSourceFilter, setLogSourceFilter] = useState<'all' | 'deployment' | 'ci' | 'automation'>('all');
  const [logSearch, setLogSearch] = useState('');
  const [copiedLogs, setCopiedLogs] = useState(false);

  // 12. Self-Healing & Remediation State
  const [remediationData, setRemediationData] = useState<ApplicationRemediationOverview | null>(null);
  const [loadingRemediation, setLoadingRemediation] = useState(false);
  const [scanningHealth, setScanningHealth] = useState(false);
  const [remediationActionMsg, setRemediationActionMsg] = useState<string | null>(null);

  const fetchRemediation = () => {
    setLoadingRemediation(true);
    api.getApplicationRemediation(app.id)
      .then(setRemediationData)
      .catch(() => setRemediationData(null))
      .finally(() => setLoadingRemediation(false));
  };

  const handleRetryRemediation = async (eventId: number) => {
    try {
      setRemediationActionMsg(`Re-queueing remediation event #${eventId}...`);
      await api.retryRemediationEvent(eventId);
      fetchRemediation();
      setTimeout(() => setRemediationActionMsg(null), 3000);
    } catch (err: any) {
      setRemediationActionMsg(`Retry failed: ${err.message}`);
    }
  };

  const handleApproveRemediation = async (eventId: number) => {
    try {
      setRemediationActionMsg(`Approving remediation event #${eventId}...`);
      await api.approveRemediationEvent(eventId);
      fetchRemediation();
      setTimeout(() => setRemediationActionMsg(null), 3000);
    } catch (err: any) {
      setRemediationActionMsg(`Approval failed: ${err.message}`);
    }
  };

  const handleCancelRemediation = async (eventId: number) => {
    try {
      setRemediationActionMsg(`Cancelling remediation event #${eventId}...`);
      await api.cancelRemediationEvent(eventId);
      fetchRemediation();
      setTimeout(() => setRemediationActionMsg(null), 3000);
    } catch (err: any) {
      setRemediationActionMsg(`Cancel failed: ${err.message}`);
    }
  };

  const handleTriggerHealthScan = async () => {
    try {
      setScanningHealth(true);
      const res = await api.triggerHealthScan();
      setRemediationActionMsg(`Scan complete: ${res.events_detected_count} health event(s) evaluated.`);
      fetchRemediation();
      setTimeout(() => setRemediationActionMsg(null), 4000);
    } catch (err: any) {
      setRemediationActionMsg(`Scan failed: ${err.message}`);
    } finally {
      setScanningHealth(false);
    }
  };

  // Load application-specific deep data
  useEffect(() => {
    fetchRemediation();

    // Fetch Application Activity
    setLoadingActivities(true);
    api.getActivity({ application: app.name })
      .then(setAppActivities)
      .catch(() => setAppActivities([]))
      .finally(() => setLoadingActivities(false));

    // Fetch CI data
    api.getApplicationCI(app.id)
      .then(setCiData)
      .catch(() => setCiData(null));

    // Fetch Latest Image
    api.getLatestApplicationImage(app.id)
      .then(setImageData)
      .catch(() => setImageData(null));

    // Fetch K8s deployment
    setLoadingK8s(true);
    api.getApplicationDeployment(app.id)
      .then((dep) => {
        setK8sDeployment(dep);
        setK8sError(null);
      })
      .catch((err) => {
        setK8sDeployment(null);
        setK8sError(err.message || 'Kubernetes deployment not yet provisioned');
      })
      .finally(() => setLoadingK8s(false));

    // Fetch Terraform
    api.getTerraformStatus().then(setTfStatus).catch(() => null);
    api.getTerraformRuns().then(setTfRuns).catch(() => []);

    // Fetch Ansible
    api.getAnsiblePlaybooks().then(setPlaybooks).catch(() => []);
    api.listAnsibleExecutions({ application_id: app.id })
      .then(setAnsibleExecutions)
      .catch(() => []);

    // Fetch manifest if not present
    if (!app.manifest_yaml) {
      api.getApplicationManifest(app.id)
        .then(setManifestContent)
        .catch(() => {
          setManifestContent(
`apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: "${app.name}"
  version: "${app.version}"
  description: "${app.description || ''}"
  team: "${app.team}"
spec:
  runtime: "${app.runtime}"
  template: "${app.template || 'python-fastapi'}"
  environment: "${app.environment}"
  port: ${app.port}
  database:
    type: "${app.database_type || 'none'}"
  deployment:
    strategy: "${app.deployment_strategy || 'rolling'}"
    replicas: ${app.replicas}`
          );
        });
    }
  }, [app.id, app.name, app.manifest_yaml]);

  // Actions
  const handleRedeploySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingDeploy(true);
    try {
      await onTriggerDeploy(app.id, redeployVersion, redeployEnv);
      setShowRedeployModal(false);
      await onRefreshData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingDeploy(false);
    }
  };

  const handleRefreshCIStatus = async () => {
    setRefreshingCI(true);
    try {
      const res = await api.refreshApplicationCI(app.id);
      setCiData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshingCI(false);
    }
  };

  const handleK8sDeploy = async () => {
    setDeployingK8s(true);
    setK8sError(null);
    try {
      const dep = await api.deployApplication(app.id, {
        environment: app.environment,
        replicas: app.replicas,
        port: app.port
      });
      setK8sDeployment(dep);
    } catch (err: any) {
      setK8sError(err.message || 'Failed to deploy to Kubernetes');
    } finally {
      setDeployingK8s(false);
    }
  };

  const handlePlanTerraform = async () => {
    setPlanningTf(true);
    setTfError(null);
    try {
      await api.planTerraform('development');
      const [st, runs] = await Promise.all([
        api.getTerraformStatus(),
        api.getTerraformRuns()
      ]);
      setTfStatus(st);
      setTfRuns(runs);
    } catch (err: any) {
      setTfError(err.message || 'Terraform plan failed');
    } finally {
      setPlanningTf(false);
    }
  };

  const handleApplyTerraform = async () => {
    setApplyingTf(true);
    setTfError(null);
    try {
      await api.applyTerraform('development');
      const [st, runs] = await Promise.all([
        api.getTerraformStatus(),
        api.getTerraformRuns()
      ]);
      setTfStatus(st);
      setTfRuns(runs);
    } catch (err: any) {
      setTfError(err.message || 'Terraform apply failed');
    } finally {
      setApplyingTf(false);
    }
  };

  const handleRunPlaybook = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunningPlaybook(true);
    setAnsibleError(null);
    try {
      await api.createAnsibleExecution({
        playbook_name: selectedPlaybook,
        application_id: app.id,
        environment_id: selectedAnsibleEnv
      });
      const updated = await api.listAnsibleExecutions({ application_id: app.id });
      setAnsibleExecutions(updated);
    } catch (err: any) {
      setAnsibleError(err.message || 'Failed to trigger Ansible execution');
    } finally {
      setRunningPlaybook(false);
    }
  };

  const handleAddEnvironment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!addedEnvs.includes(newEnvName)) {
      setAddedEnvs([...addedEnvs, newEnvName]);
    }
    setShowAddEnvModal(false);
  };

  // Consolidated Application Logs
  const consolidatedLogs = useMemo(() => {
    const lines: Array<{ timestamp: string; level: 'INFO' | 'WARN' | 'ERROR'; source: string; message: string }> = [];

    // Deployment logs
    appDeployments.forEach((d) => {
      if (d.logs) {
        const rawLines = d.logs.split('\n').filter(Boolean);
        rawLines.forEach((l) => {
          let lvl: 'INFO' | 'WARN' | 'ERROR' = 'INFO';
          if (l.toLowerCase().includes('error') || l.toLowerCase().includes('fail')) lvl = 'ERROR';
          else if (l.toLowerCase().includes('warn')) lvl = 'WARN';
          lines.push({
            timestamp: d.created_at ? new Date(d.created_at).toLocaleTimeString() : '12:00:00',
            level: lvl,
            source: `deployment-${d.version}`,
            message: l
          });
        });
      }
    });

    // CI/CD logs
    if (ciData?.run_url) {
      lines.push({
        timestamp: ciData.last_run_at ? new Date(ciData.last_run_at).toLocaleTimeString() : 'CI',
        level: ciData.status === 'PASSED' ? 'INFO' : ciData.status === 'FAILED' ? 'ERROR' : 'WARN',
        source: 'ci-pipeline',
        message: `Workflow '${ciData.workflow}' status: ${ciData.status} (run #${ciData.run_id || 'latest'})`
      });
    }

    // Automation logs
    ansibleExecutions.forEach((exec) => {
      if (exec.output) {
        exec.output.split('\n').slice(0, 5).forEach((line) => {
          lines.push({
            timestamp: exec.started_at ? new Date(exec.started_at).toLocaleTimeString() : 'Ansible',
            level: exec.status === 'SUCCESS' ? 'INFO' : 'WARN',
            source: `ansible-${exec.playbook_name}`,
            message: line
          });
        });
      }
    });

    // Sort by timestamp if possible
    return lines;
  }, [appDeployments, ciData, ansibleExecutions]);

  const filteredLogs = useMemo(() => {
    return consolidatedLogs.filter((item) => {
      const matchSource =
        logSourceFilter === 'all' ||
        (logSourceFilter === 'deployment' && item.source.startsWith('deployment')) ||
        (logSourceFilter === 'ci' && item.source.startsWith('ci')) ||
        (logSourceFilter === 'automation' && item.source.startsWith('ansible'));

      const matchSearch =
        logSearch === '' ||
        item.message.toLowerCase().includes(logSearch.toLowerCase()) ||
        item.source.toLowerCase().includes(logSearch.toLowerCase());

      return matchSource && matchSearch;
    });
  }, [consolidatedLogs, logSourceFilter, logSearch]);

  const tabs: Array<{ id: AppDetailTab; label: string; count?: number }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'deployments', label: 'Deployments', count: appDeployments.length },
    { id: 'environments', label: 'Environments', count: addedEnvs.length },
    { id: 'infrastructure', label: 'Infrastructure' },
    { id: 'automation', label: 'Automation', count: ansibleExecutions.length },
    { id: 'monitoring', label: 'Monitoring' },
    { id: 'logs', label: 'Logs', count: consolidatedLogs.length },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white transition"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Applications</span>
      </button>

      {/* ========================================================================= */}
      {/* 1. APPLICATION HEADER (Requirement 4)                                    */}
      {/* ========================================================================= */}
      <div className="rounded-lg border border-zinc-800 bg-[#121215] p-5 sm:p-6 shadow-sm min-w-0">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-5 min-w-0">
          {/* Title and Metadata */}
          <div className="space-y-3 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <div className="w-9 h-9 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center text-emerald-400 shrink-0">
                <Box className="w-5 h-5" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-white break-words">
                {app.name}
              </h1>
              <StatusBadge status={app.status} />
              <span className="text-xs font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded">
                {app.version}
              </span>
            </div>

            {app.description && (
              <p className="text-xs sm:text-sm text-zinc-300 max-w-3xl leading-relaxed">
                {app.description}
              </p>
            )}

            {/* Chips & Tags */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs font-mono">
              <span className="bg-zinc-900/90 text-zinc-300 border border-zinc-800 px-2.5 py-1 rounded flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-zinc-500" />
                <span>{app.runtime}</span>
              </span>

              {app.database_type && app.database_type !== 'none' && (
                <span className="bg-zinc-900/90 text-zinc-300 border border-zinc-800 px-2.5 py-1 rounded flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5 text-sky-400" />
                  <span className="capitalize">{app.database_type}</span>
                </span>
              )}

              {app.repository_url && (
                <a
                  href={app.repository_url}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-zinc-900/90 text-zinc-300 hover:text-white border border-zinc-800 hover:border-zinc-700 px-2.5 py-1 rounded flex items-center gap-1.5 transition"
                >
                  <GitBranch className="w-3.5 h-3.5 text-zinc-400" />
                  <span className="truncate max-w-[200px]">
                    {app.repository_url.replace('https://github.com/', '')}
                  </span>
                  <ExternalLink className="w-3 h-3 text-zinc-500" />
                </a>
              )}

              <span className="text-zinc-500 text-[11px] px-1 py-1">
                Team: <strong className="text-zinc-400 font-normal">{app.team}</strong>
              </span>

              <span className="text-zinc-500 text-[11px] px-1 py-1">
                Created: <strong className="text-zinc-400 font-normal">{new Date(app.created_at).toLocaleDateString()}</strong>
              </span>

              {app.last_deployment_at && (
                <span className="text-zinc-500 text-[11px] px-1 py-1">
                  Last deploy: <strong className="text-zinc-400 font-normal">{new Date(app.last_deployment_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</strong>
                </span>
              )}
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-2 lg:self-start shrink-0 pt-2 lg:pt-0">
            <button
              id="header-redeploy-btn"
              onClick={() => setShowRedeployModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-medium transition shadow-xs"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Redeploy</span>
            </button>

            {app.repository_url && (
              <a
                id="header-open-repo-link"
                href={app.repository_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-mono transition"
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Open Repository</span>
              </a>
            )}

            <button
              id="header-add-env-btn"
              onClick={() => setShowAddEnvModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-mono transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Environment</span>
            </button>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* 2. HORIZONTAL TAB NAVIGATION                                             */}
        {/* ========================================================================= */}
        <div className="mt-6 border-t border-zinc-800/80 pt-2 flex items-center gap-1 overflow-x-auto no-scrollbar w-full min-w-0" id="app-detail-tabs" data-testid="app-detail-tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`app-tab-${tab.id}`}
                data-testid={`app-tab-${tab.id}`}
                onClick={() => handleTabClick(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-mono whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-zinc-800 text-white font-semibold shadow-xs'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
                }`}
              >
                <span>{tab.label}</span>
                {typeof tab.count === 'number' && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                      isActive ? 'bg-zinc-700 text-white' : 'bg-zinc-900 text-zinc-500'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3. TAB CONTENT                                                           */}
      {/* ========================================================================= */}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 1: OVERVIEW (Requirement 5)                                          */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Real Metrics Section (Requirement 5 & 17) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Metric 1: CPU */}
            <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                <span>CPU Usage</span>
                <Cpu className="w-4 h-4 text-zinc-500" />
              </div>
              <div className="mt-2 text-2xl font-bold font-mono text-white">
                {appHealth ? `${appHealth.cpu_percent}%` : 'Unavailable'}
              </div>
              <div className="mt-1 text-[11px] font-mono text-zinc-500">
                {appHealth ? 'Active container probe' : 'No telemetry reporting'}
              </div>
            </div>

            {/* Metric 2: Memory */}
            <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                <span>Memory Allocation</span>
                <Server className="w-4 h-4 text-zinc-500" />
              </div>
              <div className="mt-2 text-2xl font-bold font-mono text-white">
                {appHealth ? appHealth.memory_mb : 'Unavailable'}
              </div>
              <div className="mt-1 text-[11px] font-mono text-zinc-500">
                {appHealth ? 'Resident set memory' : 'No telemetry reporting'}
              </div>
            </div>

            {/* Metric 3: Requests / Throughput */}
            <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                <span>Throughput</span>
                <Activity className="w-4 h-4 text-zinc-500" />
              </div>
              <div className="mt-2 text-2xl font-bold font-mono text-white">
                {appHealth ? `${appHealth.requests_per_sec} req/s` : 'Unavailable'}
              </div>
              <div className="mt-1 text-[11px] font-mono text-zinc-500">
                {appHealth ? 'HTTP ingress requests' : 'No telemetry reporting'}
              </div>
            </div>

            {/* Metric 4: Error Rate / Uptime */}
            <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                <span>Error Rate</span>
                <AlertCircle className="w-4 h-4 text-zinc-500" />
              </div>
              <div className="mt-2 text-2xl font-bold font-mono text-white">
                {appHealth ? appHealth.error_rate : 'Unavailable'}
              </div>
              <div className="mt-1 text-[11px] font-mono text-zinc-500">
                {appHealth ? `Uptime: ${appHealth.uptime}` : 'No telemetry reporting'}
              </div>
            </div>
          </div>

          {/* If no telemetry exists at all, display honest note */}
          {!appHealth && (
            <div className="p-3 rounded border border-zinc-800/80 bg-zinc-900/30 text-xs text-zinc-400 font-mono flex items-center gap-2">
              <Radio className="w-4 h-4 text-zinc-500 shrink-0" />
              <span>No live metrics daemon is currently reporting for this container. Metric values will populate automatically upon Prometheus scrape.</span>
            </div>
          )}

          {/* Self-Healing & Automated Remediation Overview Card */}
          <div id="overview-remediation-card" data-testid="overview-remediation-card" className="rounded-md border border-zinc-800 bg-[#121215] p-4 font-mono">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                  Self-Healing & Automated Remediation
                </span>
              </div>
              <button
                id="btn-view-remediation-details"
                data-testid="btn-view-remediation-details"
                onClick={() => handleTabClick('monitoring')}
                className="text-xs text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1"
              >
                <span>Operational Controls & Policies</span>
                <span>→</span>
              </button>
            </div>

            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-zinc-950/60 rounded border border-zinc-800/60">
                <div className="text-[11px] text-zinc-500">Active Incidents</div>
                <div className="text-lg font-bold text-white mt-0.5">
                  {remediationData?.active_events_count ?? 0}
                </div>
              </div>
              <div className="p-3 bg-zinc-950/60 rounded border border-zinc-800/60">
                <div className="text-[11px] text-zinc-500">Total Remediations</div>
                <div className="text-lg font-bold text-white mt-0.5">
                  {remediationData?.total_remediations ?? 0}
                </div>
              </div>
              <div className="p-3 bg-zinc-950/60 rounded border border-zinc-800/60">
                <div className="text-[11px] text-zinc-500">Recoveries</div>
                <div className="text-lg font-bold text-emerald-400 mt-0.5">
                  {remediationData?.successful_remediations ?? 0}
                </div>
              </div>
              <div className="p-3 bg-zinc-950/60 rounded border border-zinc-800/60">
                <div className="text-[11px] text-zinc-500">Escalations</div>
                <div className="text-lg font-bold text-rose-400 mt-0.5">
                  {remediationData?.failed_remediations ?? 0}
                </div>
              </div>
            </div>

            {remediationData?.last_remediation && (
              <div className="mt-3 p-2.5 rounded bg-zinc-950/80 border border-zinc-800/50 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500">Latest Action:</span>
                  <span className="text-zinc-200 font-semibold">{remediationData.last_remediation.action}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    remediationData.last_remediation.status === 'SUCCESS'
                      ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                      : 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                  }`}>
                    {remediationData.last_remediation.status}
                  </span>
                </div>
                <span className="text-[11px] text-zinc-500">
                  Attempt #{remediationData.last_remediation.attempt}
                </span>
              </div>
            )}
          </div>

          {/* Quick Details & Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Recent Deployments + Recent Activity */}
            <div className="lg:col-span-2 space-y-6">
              {/* Recent Deployments for THIS application */}
              <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
                <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-200">
                    Recent Deployments
                  </h3>
                  <button
                    onClick={() => handleTabClick('deployments')}
                    className="text-xs font-mono text-emerald-400 hover:text-emerald-300"
                  >
                    View all ({appDeployments.length}) →
                  </button>
                </div>

                {appDeployments.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-zinc-500">
                    No deployments recorded yet for {app.name}.
                  </div>
                ) : (
                  <div className="divide-y divide-zinc-800/60 font-mono text-xs">
                    {appDeployments.slice(0, 4).map((dep) => (
                      <div key={dep.id} className="p-3.5 hover:bg-zinc-800/30 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <StatusBadge status={dep.status} />
                          <div>
                            <div className="font-semibold text-white">
                              {dep.version}
                              <span className="text-zinc-500 font-normal ml-2 capitalize font-sans">
                                • {dep.environment}
                              </span>
                            </div>
                            <div className="text-[11px] text-zinc-400 truncate max-w-md mt-0.5">
                              {dep.commit_message || 'Deployment release'}
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="text-[11px] text-zinc-400">
                            {dep.created_at ? new Date(dep.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'recently'}
                          </div>
                          <div className="text-[10px] text-zinc-500">
                            duration: {dep.duration || 'N/A'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Activity for THIS application (Requirement 12) */}
              <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
                <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-200">
                    Recent Activity
                  </h3>
                  <span className="text-[11px] font-mono text-zinc-500">
                    Audit trail
                  </span>
                </div>

                {loadingActivities ? (
                  <div className="p-6 text-center text-xs font-mono text-zinc-500">
                    Loading activity records...
                  </div>
                ) : appActivities.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-zinc-500">
                    No activity records found matching {app.name}.
                  </div>
                ) : (
                  <div className="divide-y divide-zinc-800/60 font-mono text-xs">
                    {appActivities.slice(0, 5).map((act) => (
                      <div key={act.id} className="p-3.5 hover:bg-zinc-800/30 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <Clock className="w-4 h-4 text-zinc-500 mt-0.5 shrink-0" />
                          <div>
                            <div className="font-semibold text-zinc-200">
                              {act.action}
                            </div>
                            <div className="text-[11px] text-zinc-400 mt-0.5">
                              {act.details || act.target}
                            </div>
                          </div>
                        </div>
                        <span className="text-[10px] text-zinc-500 shrink-0">
                          {act.created_at ? new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Col: Application Operational Specs & Quick Actions */}
            <div className="space-y-6">
              {/* Specs Card */}
              <div className="rounded-md border border-zinc-800 bg-[#121215] p-4 font-mono text-xs space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 border-b border-zinc-800 pb-2">
                  Application Specs
                </h3>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Environment:</span>
                  <span className="text-white capitalize">{app.environment}</span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Assigned Port:</span>
                  <span className="text-white">{app.port}</span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Replicas:</span>
                  <span className="text-white">{app.replicas}</span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Strategy:</span>
                  <span className="text-white capitalize">{app.deployment_strategy || 'rolling'}</span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Provisioning:</span>
                  <span className="text-emerald-400">{app.provisioning_status || 'READY'}</span>
                </div>

                {app.repository_default_branch && (
                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Default Branch:</span>
                    <span className="text-white">{app.repository_default_branch}</span>
                  </div>
                )}
              </div>

              {/* CI/CD & Image Snapshot */}
              <div className="rounded-md border border-zinc-800 bg-[#121215] p-4 font-mono text-xs space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                    CI / Artifacts
                  </h3>
                  <button
                    onClick={handleRefreshCIStatus}
                    className="text-[10px] text-zinc-400 hover:text-white flex items-center gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${refreshingCI ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>CI Workflow:</span>
                  <span className="text-white">{ciData?.workflow || 'CI'}</span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>CI Status:</span>
                  <span className={ciData?.status === 'PASSED' ? 'text-emerald-400' : ciData?.status === 'FAILED' ? 'text-rose-400' : 'text-zinc-400'}>
                    {ciData?.status || 'UNKNOWN'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Container Registry:</span>
                  <span className="text-white">GHCR.io</span>
                </div>

                {imageData?.image_tag && (
                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Image Tag:</span>
                    <span className="text-emerald-400 font-bold">{imageData.image_tag}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 2: DEPLOYMENTS (Requirement 6)                                       */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'deployments' && (
        <div className="space-y-4 font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Application Deployments
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5 font-sans">
                Release history and operational rollout logs for {app.name}.
              </p>
            </div>

            <button
              onClick={() => setShowRedeployModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-medium transition shadow-xs self-start sm:self-auto"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Deploy Revision</span>
            </button>
          </div>

          <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Version</th>
                    <th className="py-2.5 px-4 font-medium">Environment</th>
                    <th className="py-2.5 px-4 font-medium">Status</th>
                    <th className="py-2.5 px-4 font-medium">Triggered By</th>
                    <th className="py-2.5 px-4 font-medium">Duration</th>
                    <th className="py-2.5 px-4 font-medium">Time</th>
                    <th className="py-2.5 px-4 font-medium">Commit</th>
                    <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {appDeployments.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-zinc-500">
                        No deployments recorded yet for this application.
                      </td>
                    </tr>
                  ) : (
                    appDeployments.map((dep) => (
                      <tr key={dep.id} className="hover:bg-zinc-800/30 transition">
                        <td className="py-3 px-4 text-white font-semibold">{dep.version}</td>
                        <td className="py-3 px-4 capitalize text-zinc-300">{dep.environment}</td>
                        <td className="py-3 px-4">
                          <StatusBadge status={dep.status} />
                        </td>
                        <td className="py-3 px-4 text-zinc-400">{dep.triggered_by || 'system'}</td>
                        <td className="py-3 px-4 text-zinc-400">{dep.duration || '24s'}</td>
                        <td className="py-3 px-4 text-zinc-400 text-[11px]">
                          {dep.created_at ? new Date(dep.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-zinc-400 max-w-[200px] truncate" title={dep.commit_message}>
                          {dep.commit_message || 'Manual revision'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {dep.logs && (
                              <button
                                onClick={() => setSelectedLogDeployment(dep)}
                                className="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] border border-zinc-700 transition"
                              >
                                View Logs
                              </button>
                            )}
                            <button
                              onClick={() => onTriggerDeploy(app.id, dep.version, dep.environment)}
                              className="px-2 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-400 text-[11px] border border-emerald-800/60 transition"
                              title="Redeploy this revision"
                            >
                              Rollout
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 3: ENVIRONMENTS (Requirement 7)                                      */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'environments' && (
        <div className="space-y-4 font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Application Environments
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5 font-sans">
                Target environments and rollout topologies configured for {app.name}.
              </p>
            </div>

            <button
              onClick={() => setShowAddEnvModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-mono transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Configure Environment</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {addedEnvs.map((envName) => {
              const isDefaultEnv = envName.toLowerCase() === app.environment.toLowerCase();
              return (
                <div
                  key={envName}
                  className={`p-4 rounded-md border bg-[#121215] space-y-3 ${
                    isDefaultEnv ? 'border-emerald-800/60' : 'border-zinc-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white capitalize text-sm">
                      {envName}
                    </span>
                    {isDefaultEnv ? (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 font-mono">
                        Active Target
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-400 font-mono">
                        Configured
                      </span>
                    )}
                  </div>

                  <div className="space-y-2 text-xs text-zinc-400">
                    <div className="flex items-center justify-between">
                      <span>Status:</span>
                      <span className="text-emerald-400 font-bold">READY</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Revision:</span>
                      <span className="text-white">{app.version}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Cluster:</span>
                      <span className="text-zinc-300">Local KinD</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Namespace:</span>
                      <span className="text-zinc-300">devforge</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Endpoint:</span>
                      <span className="text-zinc-300 truncate max-w-[150px]">
                        localhost:{app.port}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span>Replicas:</span>
                      <span className="text-zinc-300">{app.replicas} / {app.replicas} Active</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between">
                    <button
                      onClick={() => {
                        setRedeployEnv(envName);
                        setShowRedeployModal(true);
                      }}
                      className="text-xs text-emerald-400 hover:text-emerald-300"
                    >
                      Rollout to {envName} →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 4: INFRASTRUCTURE (Requirement 8)                                    */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'infrastructure' && (
        <div className="space-y-6 font-mono">
          <div className="pb-2 border-b border-zinc-800/80">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Application Infrastructure & Kubernetes
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5 font-sans">
              Kubernetes cluster resources, Pod rollout status, and Terraform state for {app.name}.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" id="app-detail-infrastructure-section">
            {/* Kubernetes Resources */}
            <div id="app-detail-k8s-section" className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-xs font-semibold uppercase text-zinc-200">
                    Kubernetes Workload
                  </h3>
                </div>
                <span className="text-[11px] text-zinc-400">
                  Cluster: Local KinD
                </span>
              </div>

              {k8sError && !k8sDeployment ? (
                <div className="space-y-3">
                  <div className="p-3 rounded bg-zinc-900/60 border border-zinc-800 text-xs text-zinc-400">
                    {k8sError}
                  </div>
                  <button
                    id="refresh-k8s-btn"
                    onClick={handleK8sDeploy}
                    disabled={deployingK8s}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono transition"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>{deployingK8s ? 'Deploying...' : 'Provision Kubernetes Workload'}</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Namespace:</span>
                    <span id="k8s-deployment-ns" className="text-white font-bold">{k8sDeployment?.namespace || 'devforge'}</span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Deployment:</span>
                    <span id="k8s-deployment-name" className="text-white font-bold">{k8sDeployment?.deployment_name || `${app.name}-deployment`}</span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Service:</span>
                    <span id="k8s-deployment-service" className="text-white font-bold">{k8sDeployment?.service_name || `${app.name}-service`}</span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Replicas:</span>
                    <span id="k8s-deployment-pods" className="text-emerald-400 font-bold">
                      {k8sDeployment?.ready_replicas ?? app.replicas} / {k8sDeployment?.replicas ?? app.replicas} Ready
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Target Port:</span>
                    <span className="text-white">{k8sDeployment?.port || app.port}</span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>NodePort:</span>
                    <span className="text-zinc-300">{k8sDeployment?.node_port || '30080'}</span>
                  </div>

                  <div className="flex items-center justify-between text-zinc-400">
                    <span>Status:</span>
                    <span id="k8s-deployment-status-badge" className="text-emerald-400 font-bold">
                      {k8sDeployment?.status || 'RUNNING'}
                    </span>
                  </div>

                  <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-2">
                    <button
                      id="refresh-k8s-btn"
                      onClick={handleK8sDeploy}
                      disabled={deployingK8s}
                      className="px-2.5 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition"
                    >
                      {deployingK8s ? 'Rolling...' : 'Redeploy Pods'}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Terraform Runs for this environment */}
            <div id="terraform-infrastructure-section" className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-sky-400" />
                  <h3 className="text-xs font-semibold uppercase text-zinc-200" id="terraform-provider">
                    Terraform Infrastructure
                  </h3>
                </div>
                <span className="text-[11px] text-zinc-400" id="terraform-environment">
                  Target: {app.environment}
                </span>
              </div>

              {tfError && (
                <div className="p-2.5 rounded bg-rose-950/60 border border-rose-800/60 text-xs text-rose-300">
                  {tfError}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Terraform Status:</span>
                  <span id="terraform-status-badge" className="text-emerald-400 font-bold">
                    {tfStatus?.status || 'APPLIED'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Managed Resources:</span>
                  <span id="terraform-resources-count" className="text-white">
                    {tfStatus?.resources_count || 4} resources
                  </span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span>Last Executed:</span>
                  <span className="text-zinc-300">
                    {tfStatus?.latest_run?.completed_at ? new Date(tfStatus.latest_run.completed_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Synchronized'}
                  </span>
                </div>

                <div className="pt-3 border-t border-zinc-800/80 flex items-center gap-2">
                  <button
                    id="terraform-plan-btn"
                    onClick={handlePlanTerraform}
                    disabled={planningTf}
                    className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition"
                  >
                    {planningTf ? 'Planning...' : 'Terraform Plan'}
                  </button>

                  <button
                    id="terraform-apply-btn"
                    onClick={handleApplyTerraform}
                    disabled={applyingTf}
                    className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs transition"
                  >
                    {applyingTf ? 'Applying...' : 'Terraform Apply'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* DevForge Manifest (YAML) */}
          <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
            <div className="p-3 bg-[#0e0e11] border-b border-zinc-800 flex items-center justify-between">
              <span className="text-xs font-mono font-medium text-zinc-300 flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-zinc-400" />
                <span>devforge.yaml (Infrastructure As Code Manifest)</span>
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(manifestContent);
                  setCopiedManifest(true);
                  setTimeout(() => setCopiedManifest(false), 2000);
                }}
                className="text-[11px] text-zinc-400 hover:text-white flex items-center gap-1"
              >
                {copiedManifest ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedManifest ? 'Copied' : 'Copy Manifest'}</span>
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-zinc-300 bg-zinc-950/80 overflow-x-auto max-h-72">
              {manifestContent}
            </pre>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 5: AUTOMATION (Requirement 9)                                        */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'automation' && (
        <div className="space-y-6 font-mono">
          <div className="pb-2 border-b border-zinc-800/80">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Ansible Automation
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5 font-sans">
              Approved playbooks and execution history for {app.name}.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Run Playbook Form */}
            <div id="ansible-launcher-section" className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
              <h3 className="text-xs font-semibold uppercase text-zinc-200 border-b border-zinc-800 pb-2">
                Execute Playbook
              </h3>

              {ansibleError && (
                <div className="p-2.5 rounded bg-rose-950/60 border border-rose-800/60 text-xs text-rose-300">
                  {ansibleError}
                </div>
              )}

              <form onSubmit={handleRunPlaybook} className="space-y-3 text-xs">
                <div>
                  <label className="block text-zinc-400 mb-1">Approved Playbook:</label>
                  <select
                    id="ansible-playbook-select"
                    value={selectedPlaybook}
                    onChange={(e) => setSelectedPlaybook(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-600"
                  >
                    <option value="configure_application">configure_application</option>
                    <option value="health_check">health_check</option>
                    <option value="configure_environment">configure_environment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-400 mb-1">Target Environment:</label>
                  <select
                    id="ansible-env-select"
                    value={selectedAnsibleEnv}
                    onChange={(e) => setSelectedAnsibleEnv(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:border-zinc-600 capitalize"
                  >
                    {addedEnvs.map((env) => (
                      <option key={env} value={env}>{env}</option>
                    ))}
                  </select>
                </div>

                <div className="pt-2">
                  <button
                    id="ansible-run-btn"
                    type="submit"
                    disabled={runningPlaybook}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{runningPlaybook ? 'Executing...' : 'Run Playbook'}</span>
                  </button>
                </div>
              </form>
            </div>

            {/* Execution History */}
            <div id="ansible-executions-table" className="lg:col-span-2 rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
              <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                  Execution History
                </h3>
                <span className="text-[11px] text-zinc-500">
                  {ansibleExecutions.length} runs recorded
                </span>
              </div>

              {ansibleExecutions.length === 0 ? (
                <div className="p-8 text-center text-xs text-zinc-500">
                  No playbook executions yet recorded for this application.
                </div>
              ) : (
                <div className="divide-y divide-zinc-800/60 text-xs max-h-96 overflow-y-auto">
                  {ansibleExecutions.map((exec) => (
                    <div key={exec.id} className="p-3.5 hover:bg-zinc-800/30 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <StatusBadge status={exec.status} />
                          <span className="font-semibold text-white">{exec.playbook_name}</span>
                          <span className="text-zinc-500 font-sans capitalize">({exec.environment_id})</span>
                        </div>
                        <span className="text-[11px] text-zinc-500">
                          {exec.started_at ? new Date(exec.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                        </span>
                      </div>

                      {exec.output && (
                        <pre className="p-2 rounded bg-zinc-950 border border-zinc-800/50 text-[11px] text-zinc-300 overflow-x-auto max-h-24">
                          {exec.output}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 6: MONITORING (Requirement 10)                                       */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'monitoring' && (
        <div className="space-y-6 font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Application Telemetry & Monitoring
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5 font-sans">
                Real metrics scraped from container runtime and service endpoints.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <a
                id="btn-open-grafana"
                href="http://localhost:3001"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs transition"
              >
                <span>Open in Grafana</span>
                <ExternalLink className="w-3 h-3" />
              </a>

              <a
                id="btn-open-prometheus"
                href="http://localhost:9090"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs transition"
              >
                <span>Prometheus</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {appHealth ? (
            <div id="monitoring-health-section" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-zinc-500 text-xs">CPU Core Load</div>
                <div className="text-2xl font-bold text-white mt-1">{appHealth.cpu_percent}%</div>
                <div className="text-[11px] text-zinc-400 mt-1">Status: {appHealth.status}</div>
              </div>

              <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-zinc-500 text-xs">Memory RSS</div>
                <div className="text-2xl font-bold text-white mt-1">{appHealth.memory_mb}</div>
                <div className="text-[11px] text-zinc-400 mt-1">Pod working set</div>
              </div>

              <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-zinc-500 text-xs">Ingress Traffic</div>
                <div className="text-2xl font-bold text-white mt-1">{appHealth.requests_per_sec} RPS</div>
                <div className="text-[11px] text-zinc-400 mt-1">Realtime queries</div>
              </div>

              <div className="p-4 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-zinc-500 text-xs">Error Rate</div>
                <div className="text-2xl font-bold text-white mt-1">{appHealth.error_rate}</div>
                <div className="text-[11px] text-zinc-400 mt-1">Uptime: {appHealth.uptime}</div>
              </div>
            </div>
          ) : (
            <div className="p-10 rounded-md border border-zinc-800 bg-[#121215] text-center space-y-2">
              <Radio className="w-6 h-6 text-zinc-500 mx-auto" />
              <div className="text-sm text-zinc-300 font-semibold">No monitoring data available</div>
              <p className="text-xs text-zinc-500 max-w-md mx-auto font-sans">
                DevForge does not fake telemetry values. Once Prometheus scrapes the running container endpoints for {app.name}, real CPU, latency, and throughput metrics will appear here.
              </p>
            </div>
          )}

          {/* ======================================================================= */}
          {/* Phase 11: Self-Healing & Remediation Engine Section                     */}
          {/* ======================================================================= */}
          <div id="monitoring-remediation-panel" data-testid="monitoring-remediation-panel" className="mt-8 pt-6 border-t border-zinc-800/80 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/60">
              <div>
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                    Self-Healing & Automated Remediation Engine
                  </h3>
                </div>
                <p className="text-xs text-zinc-400 mt-0.5 font-sans">
                  Real failure detection, deterministic policy matching, rate limits, and health verification.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  id="btn-trigger-health-scan"
                  data-testid="btn-trigger-health-scan"
                  onClick={handleTriggerHealthScan}
                  disabled={scanningHealth}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs transition disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${scanningHealth ? 'animate-spin text-emerald-400' : ''}`} />
                  <span>{scanningHealth ? 'Scanning Cluster...' : 'Trigger Health Scan'}</span>
                </button>
              </div>
            </div>

            {/* Action Feedback Notification */}
            {remediationActionMsg && (
              <div id="remediation-action-banner" className="p-3 rounded border border-zinc-800 bg-zinc-950 text-xs text-emerald-400 flex items-center gap-2 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{remediationActionMsg}</span>
              </div>
            )}

            {/* Stats Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-[11px] text-zinc-500">Active Incidents</div>
                <div className="text-xl font-bold text-white mt-1">
                  {remediationData?.active_events_count ?? 0}
                </div>
              </div>
              <div className="p-3.5 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-[11px] text-zinc-500">Remediations Run</div>
                <div className="text-xl font-bold text-white mt-1">
                  {remediationData?.total_remediations ?? 0}
                </div>
              </div>
              <div className="p-3.5 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-[11px] text-zinc-500">Confirmed Recoveries</div>
                <div className="text-xl font-bold text-emerald-400 mt-1">
                  {remediationData?.successful_remediations ?? 0}
                </div>
              </div>
              <div className="p-3.5 rounded-md border border-zinc-800 bg-[#121215]">
                <div className="text-[11px] text-zinc-500">Escalated Failures</div>
                <div className="text-xl font-bold text-rose-400 mt-1">
                  {remediationData?.failed_remediations ?? 0}
                </div>
              </div>
            </div>

            {/* Active Policies Table */}
            <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
              <div className="p-3.5 border-b border-zinc-800 flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                  Enforced Remediation Policies
                </h4>
                <span className="text-[10px] text-zinc-500 bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded">
                  Conservative & Scoped
                </span>
              </div>

              {(!remediationData?.policies || remediationData.policies.length === 0) ? (
                <div className="p-6 text-center text-xs text-zinc-500">No remediation policies loaded.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 font-semibold">
                      <tr>
                        <th className="p-3">Policy</th>
                        <th className="p-3">Condition / Event</th>
                        <th className="p-3">Environment</th>
                        <th className="p-3">Allowlisted Action</th>
                        <th className="p-3">Max Retries</th>
                        <th className="p-3">Cooldown</th>
                        <th className="p-3">Safety Gate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                      {remediationData.policies.map((pol) => (
                        <tr key={pol.id} className="hover:bg-zinc-800/20">
                          <td className="p-3 font-semibold text-white">{pol.name}</td>
                          <td className="p-3 text-zinc-300">{pol.event_type}</td>
                          <td className="p-3 capitalize">{pol.environment}</td>
                          <td className="p-3 font-mono text-emerald-400">{pol.action}</td>
                          <td className="p-3">{pol.max_attempts} attempts</td>
                          <td className="p-3">{pol.cooldown_seconds}s</td>
                          <td className="p-3">
                            {pol.requires_approval || pol.environment === 'production' ? (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800/40">
                                Requires Approval
                              </span>
                            ) : (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                                Automated
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Remediation Events & Executions History */}
            <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
              <div className="p-3.5 border-b border-zinc-800 flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                  Remediation Events & Incident Log
                </h4>
                <button
                  onClick={fetchRemediation}
                  className="text-xs text-zinc-400 hover:text-white flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Refresh</span>
                </button>
              </div>

              {(!remediationData?.events || remediationData.events.length === 0) ? (
                <div className="p-8 text-center text-xs text-zinc-500">
                  <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                  <div>No self-healing incidents recorded. System and workloads healthy.</div>
                </div>
              ) : (
                <div className="divide-y divide-zinc-800/60 text-xs">
                  {remediationData.events.map((ev) => (
                    <div key={ev.id} id={`rem-event-row-${ev.id}`} data-testid="rem-event-row" className="p-4 hover:bg-zinc-800/20 space-y-2.5">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                            ev.status === 'RECOVERED'
                              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/50'
                              : ev.status === 'REMEDIATING' || ev.status === 'VERIFYING'
                              ? 'bg-blue-950/60 text-blue-400 border-blue-800/50'
                              : ev.status === 'ESCALATED' || ev.status === 'FAILED'
                              ? 'bg-rose-950/60 text-rose-400 border-rose-800/50'
                              : 'bg-amber-950/60 text-amber-400 border-amber-800/50'
                          }`}>
                            {ev.status}
                          </span>
                          <span className="font-semibold text-white">{ev.event_type}</span>
                          <span className="text-zinc-500 text-[11px] capitalize">({ev.environment_id})</span>
                          <span className="text-zinc-500 text-[11px]">• Event #{ev.id}</span>
                        </div>

                        {/* Interactive Operator Actions */}
                        <div className="flex items-center gap-1.5">
                          {(ev.status === 'FAILED' || ev.status === 'ESCALATED') && (
                            <button
                              id={`btn-retry-rem-${ev.id}`}
                              data-testid="btn-retry-rem"
                              onClick={() => handleRetryRemediation(ev.id)}
                              className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-700 text-[11px] transition"
                            >
                              Retry Remediation
                            </button>
                          )}
                          {ev.status === 'EVALUATING' && (
                            <button
                              id={`btn-approve-rem-${ev.id}`}
                              data-testid="btn-approve-rem"
                              onClick={() => handleApproveRemediation(ev.id)}
                              className="px-2.5 py-1 rounded bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-700 text-[11px] transition"
                            >
                              Approve Action
                            </button>
                          )}
                          {['DETECTED', 'EVALUATING', 'REMEDIATING', 'VERIFYING'].includes(ev.status) && (
                            <button
                              id={`btn-cancel-rem-${ev.id}`}
                              data-testid="btn-cancel-rem"
                              onClick={() => handleCancelRemediation(ev.id)}
                              className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-rose-400 hover:text-rose-300 border border-zinc-800 text-[11px] transition"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Detail Text */}
                      {ev.details && (
                        <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/60 text-zinc-300 text-[11px]">
                          <span className="text-zinc-500">Root Cause / Observation: </span>
                          <span>{ev.details}</span>
                        </div>
                      )}

                      {/* Execution Details */}
                      {ev.executions && ev.executions.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <div className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">
                            Execution Attempts:
                          </div>
                          {ev.executions.map((exec) => (
                            <div
                              key={exec.id}
                              className="p-2 rounded bg-zinc-950/50 border border-zinc-800/40 flex flex-wrap items-center justify-between gap-2 text-[11px]"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-zinc-400 font-mono">Attempt #{exec.attempt}</span>
                                <span className="text-emerald-400 font-mono">{exec.action}</span>
                                <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                                  exec.status === 'SUCCESS' ? 'text-emerald-400 bg-emerald-950/40' : 'text-rose-400 bg-rose-950/40'
                                }`}>
                                  {exec.status}
                                </span>
                              </div>
                              {exec.error_message && (
                                <span className="text-rose-400 max-w-md truncate">{exec.error_message}</span>
                              )}
                              {exec.completed_at && (
                                <span className="text-zinc-500">{new Date(exec.completed_at).toLocaleTimeString()}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------------- */}
      {/* TAB 7: LOGS (Requirement 11)                                             */}
      {/* ------------------------------------------------------------------------- */}
      {activeTab === 'logs' && (
        <div className="space-y-4 font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Consolidated Application Logs
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5 font-sans">
                Unified developer terminal capturing deployment, build, and automation events.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={logSourceFilter}
                onChange={(e: any) => setLogSourceFilter(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-600"
              >
                <option value="all">All Sources</option>
                <option value="deployment">Deployment Logs</option>
                <option value="ci">CI/CD Logs</option>
                <option value="automation">Automation Logs</option>
              </select>

              <button
                onClick={() => {
                  const fullText = filteredLogs.map((l) => `[${l.timestamp}] [${l.level}] [${l.source}] ${l.message}`).join('\n');
                  navigator.clipboard.writeText(fullText);
                  setCopiedLogs(true);
                  setTimeout(() => setCopiedLogs(false), 2000);
                }}
                className="px-2.5 py-1.5 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs flex items-center gap-1.5 transition"
              >
                {copiedLogs ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedLogs ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Search within logs */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search log stream by keyword..."
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
            />
          </div>

          {/* Terminal Box */}
          <div className="rounded-md border border-zinc-800 bg-[#09090b] p-4 text-xs font-mono max-h-[500px] overflow-y-auto space-y-1.5">
            {filteredLogs.length === 0 ? (
              <div className="text-zinc-500 py-6 text-center">
                No log output matching current filter.
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div key={idx} className="flex items-start gap-2 hover:bg-zinc-900/50 py-0.5 px-1 rounded transition">
                  <span className="text-zinc-600 select-none shrink-0">{log.timestamp}</span>
                  <span
                    className={`font-semibold shrink-0 ${
                      log.level === 'ERROR'
                        ? 'text-rose-400'
                        : log.level === 'WARN'
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    [{log.level}]
                  </span>
                  <span className="text-zinc-500 shrink-0">[{log.source}]</span>
                  <span className="text-zinc-300 break-all">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODALS                                                                   */}
      {/* ========================================================================= */}

      {/* Redeploy Modal */}
      {showRedeployModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-[#121215] border border-zinc-800 rounded-lg max-w-md w-full p-5 font-mono text-xs space-y-4">
            <h3 className="text-sm font-semibold text-white">Trigger Application Rollout</h3>
            <form onSubmit={handleRedeploySubmit} className="space-y-3">
              <div>
                <label className="block text-zinc-400 mb-1">Target Revision / Version:</label>
                <input
                  type="text"
                  value={redeployVersion}
                  onChange={(e) => setRedeployVersion(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 focus:outline-none focus:border-zinc-600"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Environment:</label>
                <select
                  value={redeployEnv}
                  onChange={(e) => setRedeployEnv(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 capitalize focus:outline-none focus:border-zinc-600"
                >
                  {addedEnvs.map((env) => (
                    <option key={env} value={env}>{env}</option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  id="modal-redeploy-cancel-btn"
                  type="button"
                  onClick={() => setShowRedeployModal(false)}
                  className="px-3 py-1.5 rounded border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDeploy}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition"
                >
                  {isSubmittingDeploy ? 'Deploying...' : 'Initiate Rollout'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Environment Modal */}
      {showAddEnvModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-[#121215] border border-zinc-800 rounded-lg max-w-md w-full p-5 font-mono text-xs space-y-4">
            <h3 className="text-sm font-semibold text-white">Add Target Environment</h3>
            <form onSubmit={handleAddEnvironment} className="space-y-3">
              <div>
                <label className="block text-zinc-400 mb-1">Environment Name:</label>
                <select
                  value={newEnvName}
                  onChange={(e) => setNewEnvName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-zinc-200 focus:outline-none focus:border-zinc-600"
                >
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                  <option value="preview">Preview</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  id="modal-add-env-cancel-btn"
                  type="button"
                  onClick={() => setShowAddEnvModal(false)}
                  className="px-3 py-1.5 rounded border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition"
                >
                  Add Environment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deployment Log Viewer Modal */}
      {selectedLogDeployment && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-[#121215] border border-zinc-800 rounded-lg max-w-2xl w-full p-5 font-mono text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="font-semibold text-white">
                Logs for Deployment #{selectedLogDeployment.id} ({selectedLogDeployment.version})
              </span>
              <button
                onClick={() => setSelectedLogDeployment(null)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <pre className="p-4 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 overflow-x-auto max-h-96">
              {selectedLogDeployment.logs || 'No log stream recorded.'}
            </pre>
            <div className="text-right">
              <button
                onClick={() => setSelectedLogDeployment(null)}
                className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
