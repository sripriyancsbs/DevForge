import React, { useState, useEffect } from 'react';
import {
  X,
  GitBranch,
  ExternalLink,
  Play,
  Database,
  Layers,
  FileCode,
  FolderTree,
  AlertCircle,
  Copy,
  Check,
  Cpu,
  Server,
  Github
} from 'lucide-react';
import { Application, Deployment, ServiceHealth } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { api } from '../../services/api';

interface AppDetailDrawerProps {
  app: Application | null;
  onClose: () => void;
  onTriggerDeploy: (appId: number, version: string, environment: string) => void;
  deployments?: Deployment[];
  health?: ServiceHealth | null;
}

export const AppDetailDrawer: React.FC<AppDetailDrawerProps> = ({
  app,
  onClose,
  onTriggerDeploy,
  deployments = [],
  health = null
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'deployments' | 'manifest' | 'metrics'>('overview');
  const [deployVersion, setDeployVersion] = useState('v1.0.2');
  const [deployEnv, setDeployEnv] = useState('production');
  const [isDeploying, setIsDeploying] = useState(false);
  const [manifestContent, setManifestContent] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [loadingManifest, setLoadingManifest] = useState(false);

  useEffect(() => {
    if (!app) return;
    if (app.manifest_yaml) {
      setManifestContent(app.manifest_yaml);
    } else {
      setLoadingManifest(true);
      api.getApplicationManifest(app.id)
        .then((m) => setManifestContent(m))
        .catch(() => {
          // Synthesize fallback preview if legacy seed app
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
  build:
    docker: true
    dockerfile: "Dockerfile"
  deployment:
    strategy: "${app.deployment_strategy || 'rolling'}"
    replicas: ${app.replicas}
  healthCheck:
    path: "${app.runtime.includes('Go') ? '/health' : app.runtime.includes('React') ? '/' : '/healthz'}"
    port: ${app.port}`
          );
        })
        .finally(() => setLoadingManifest(false));
    }
  }, [app]);

  if (!app) return null;

  const handleDeploy = () => {
    setIsDeploying(true);
    onTriggerDeploy(app.id, deployVersion, deployEnv);
    setTimeout(() => {
      setIsDeploying(false);
    }, 1200);
  };

  const handleCopyManifest = () => {
    if (!manifestContent) return;
    navigator.clipboard.writeText(manifestContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const appDeployments = deployments.filter((d) => d.application_id === app.id);

  const getProvisioningBadge = () => {
    const status = app.provisioning_status || 'READY';
    if (status === 'READY') {
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">PROVISIONED</span>;
    }
    if (status === 'PROVISIONING' || status === 'PENDING') {
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse">PROVISIONING</span>;
    }
    return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-red-500/15 text-red-400 border border-red-500/30">FAILED</span>;
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-xl bg-[#0e0e11] border-l border-[#27272a] h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-150">
        {/* Header */}
        <div className="p-4 border-b border-[#27272a] flex items-start justify-between bg-[#121215]">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-semibold text-white font-mono">{app.name}</h2>
              <StatusBadge status={app.status} />
              {getProvisioningBadge()}
            </div>
            <p className="text-xs text-zinc-400 max-w-md">{app.description || 'No description provided.'}</p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 p-1 rounded hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action Toolbar */}
        <div className="px-4 py-2.5 bg-zinc-900/60 border-b border-[#27272a] flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <a
              href={app.repository_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 font-mono transition"
            >
              <GitBranch className="w-3 h-3 text-zinc-400" />
              <span>{app.branch}</span>
              <ExternalLink className="w-3 h-3 text-zinc-400 ml-0.5" />
            </a>
            <span className="text-zinc-600 font-mono">|</span>
            <span className="font-mono text-zinc-400">{app.runtime}</span>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={deployVersion}
              onChange={(e) => setDeployVersion(e.target.value)}
              className="w-16 px-1.5 py-1 bg-zinc-950 border border-zinc-700 text-xs font-mono text-zinc-200 rounded text-center"
              placeholder="v1.0.1"
            />
            <button
              onClick={handleDeploy}
              disabled={isDeploying}
              className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded font-medium transition disabled:opacity-50"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>{isDeploying ? 'Triggering...' : 'Deploy'}</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#27272a] bg-[#0c0c0e] px-4">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'deployments', label: `Deployments (${appDeployments.length})` },
            { id: 'manifest', label: 'Generated Configuration (devforge.yaml)' },
            { id: 'metrics', label: 'Service Telemetry' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2.5 px-3 text-xs font-medium border-b-2 transition ${
                activeTab === tab.id
                  ? 'border-emerald-500 text-white font-semibold'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {app.provisioning_error && (
                <div className="p-3 bg-red-950/40 border border-red-800 rounded text-xs text-red-200 font-mono space-y-1">
                  <div className="font-semibold flex items-center gap-1.5 text-red-400">
                    <AlertCircle className="w-4 h-4" />
                    <span>Provisioning Error Encountered:</span>
                  </div>
                  <div>{app.provisioning_error}</div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Ownership Team</div>
                  <div className="text-zinc-200 font-medium mt-1">{app.team}</div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Starter Template</div>
                  <div className="text-zinc-200 font-mono mt-1">{app.template || 'python-fastapi'}</div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Target Environment</div>
                  <div className="text-zinc-200 font-medium mt-1 uppercase font-mono">{app.environment}</div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Container Port</div>
                  <div className="text-zinc-200 font-mono mt-1">:{app.port}</div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Database Dependency</div>
                  <div className="text-zinc-200 font-mono mt-1 capitalize">{app.database_type || 'none'}</div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Deployment Strategy</div>
                  <div className="text-zinc-200 font-mono mt-1 capitalize">{app.deployment_strategy || 'rolling'}</div>
                </div>
              </div>

              {/* Workspace Location */}
              <div className="p-3 rounded border border-zinc-800 bg-[#121215] space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 text-zinc-300 font-semibold font-mono">
                  <FolderTree className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Generated Workspace Location</span>
                </div>
                <div className="text-xs font-mono text-zinc-400 bg-zinc-950 p-2 rounded border border-zinc-800 break-all">
                  {app.generated_path || `.devforge/generated/${app.name}`}
                </div>
              </div>

              <div className="p-3 rounded border border-zinc-800 bg-[#121215] space-y-2">
                <div className="text-xs font-semibold text-zinc-300">Internal Routing & Ingress</div>
                <div className="text-xs font-mono text-zinc-400 bg-zinc-950 p-2 rounded border border-zinc-800 break-all">
                  http://{app.slug}.mesh.devforge.internal:{app.port}
                </div>
              </div>

              {/* GitHub Repository Details */}
              <div className="p-3.5 rounded border border-zinc-800 bg-[#121215] space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 font-mono font-semibold text-zinc-300">
                    <Github className="w-4 h-4 text-emerald-400" />
                    <span>Repository</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300 font-normal">
                      GitHub
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400">
                    <span>Branch</span>
                    <span className="text-emerald-400 font-semibold">
                      {app.repository_default_branch || app.branch || 'main'}
                    </span>
                  </div>
                </div>

                {app.provisioning_status === 'READY' || (app.repository_owner && app.repository_name) ? (
                  <div className="flex items-center justify-between p-2.5 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono">
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-3.5 h-3.5 text-zinc-500" />
                      <span className="text-zinc-200 font-semibold">
                        {app.repository_owner && app.repository_name
                          ? `${app.repository_owner}/${app.repository_name}`
                          : (app.repository_url || '').replace(/^https:\/\/github\.com\//, '')}
                      </span>
                    </div>
                    {app.repository_url && (
                      <a
                        href={app.repository_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/30 transition text-xs font-semibold font-mono"
                      >
                        <span>Open GitHub Repository</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                ) : (
                  <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/80 text-xs font-mono text-zinc-400 flex items-center justify-between">
                    <span className="text-[11px]">
                      {app.provisioning_status === 'FAILED'
                        ? 'GitHub provisioning failed'
                        : `Provisioning in progress (${app.provisioning_status || 'PENDING'})...`}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                      {app.provisioning_status || 'PENDING'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'deployments' && (
            <div className="space-y-2">
              {appDeployments.length === 0 ? (
                <div className="p-6 text-center text-xs text-zinc-500 font-mono">
                  No previous deployments recorded for this service.
                </div>
              ) : (
                appDeployments.map((dep) => (
                  <div
                    key={dep.id}
                    className="p-3 rounded border border-zinc-800 bg-[#121215] hover:border-zinc-700 transition text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-white">{dep.version}</span>
                        <StatusBadge status={dep.status} />
                      </div>
                      <span className="text-[11px] font-mono text-zinc-500">{dep.duration}</span>
                    </div>
                    <div className="text-zinc-400 text-[11px] font-mono flex items-center gap-2">
                      <span className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300">{dep.commit_hash}</span>
                      <span className="truncate">{dep.commit_message || 'Automated deployment rollout'}</span>
                    </div>
                    {dep.logs && (
                      <pre className="p-2 rounded bg-zinc-950 border border-zinc-800 text-[11px] text-zinc-400 font-mono overflow-x-auto">
                        {dep.logs}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'manifest' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <div className="flex items-center gap-1.5 font-mono">
                  <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Generated Configuration (devforge.yaml)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-zinc-500">apiVersion: devforge/v1</span>
                  <button
                    onClick={handleCopyManifest}
                    className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 rounded text-[11px] text-zinc-300 font-mono flex items-center gap-1 transition"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
              <pre className="p-3.5 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed max-h-[600px]">
                {loadingManifest ? 'Loading manifest...' : manifestContent}
              </pre>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <span className="text-[11px] text-zinc-500 font-mono">CPU Usage</span>
                  <div className="text-lg font-mono font-semibold text-white mt-1">
                    {health ? `${health.cpu_percent}%` : '12.4%'}
                  </div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <span className="text-[11px] text-zinc-500 font-mono">Memory Allocation</span>
                  <div className="text-lg font-mono font-semibold text-white mt-1">
                    {health ? health.memory_mb : '240 MB'}
                  </div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <span className="text-[11px] text-zinc-500 font-mono">Throughput</span>
                  <div className="text-lg font-mono font-semibold text-white mt-1">
                    {health ? `${health.requests_per_sec} req/s` : '145 req/s'}
                  </div>
                </div>
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <span className="text-[11px] text-zinc-500 font-mono">Error Rate</span>
                  <div className="text-lg font-mono font-semibold text-white mt-1">
                    {health ? health.error_rate : '0.01%'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
