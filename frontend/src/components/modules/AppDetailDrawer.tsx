import React, { useState } from 'react';
import {
  X,
  GitBranch,
  ExternalLink,
  Server,
  Play,
  RotateCcw,
  Clock,
  Cpu,
  Layers,
  FileCode,
  Terminal,
  Activity,
  CheckCircle2
} from 'lucide-react';
import { Application, Deployment, ServiceHealth } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

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

  if (!app) return null;

  const handleDeploy = () => {
    setIsDeploying(true);
    onTriggerDeploy(app.id, deployVersion, deployEnv);
    setTimeout(() => {
      setIsDeploying(false);
    }, 1200);
  };

  const appDeployments = deployments.filter((d) => d.application_id === app.id);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-xl bg-[#0e0e11] border-l border-[#27272a] h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-150">
        {/* Header */}
        <div className="p-4 border-b border-[#27272a] flex items-start justify-between bg-[#121215]">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-semibold text-white font-mono">{app.name}</h2>
              <StatusBadge status={app.status} />
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
            { id: 'manifest', label: 'Manifest (devforge.yaml)' },
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
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded border border-zinc-800 bg-[#121215]">
                  <div className="text-zinc-500 font-mono text-[11px]">Ownership Team</div>
                  <div className="text-zinc-200 font-medium mt-1">{app.team}</div>
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
                  <div className="text-zinc-500 font-mono text-[11px]">Instance Replicas</div>
                  <div className="text-zinc-200 font-mono mt-1">{app.replicas} Pods</div>
                </div>
              </div>

              <div className="p-3 rounded border border-zinc-800 bg-[#121215] space-y-2">
                <div className="text-xs font-semibold text-zinc-300">Internal Routing & Ingress</div>
                <div className="text-xs font-mono text-zinc-400 bg-zinc-950 p-2 rounded border border-zinc-800 break-all">
                  http://{app.slug}.mesh.devforge.internal:{app.port}
                </div>
              </div>

              <div className="p-3 rounded border border-zinc-800 bg-[#121215] space-y-2">
                <div className="text-xs font-semibold text-zinc-300">Git Repository Origin</div>
                <div className="text-xs font-mono text-zinc-400 bg-zinc-950 p-2 rounded border border-zinc-800 break-all">
                  {app.repository_url} (branch: {app.branch})
                </div>
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
                <span className="font-mono">devforge.yaml</span>
                <span className="text-[10px] font-mono text-zinc-500">Auto-generated manifest</span>
              </div>
              <pre className="p-3 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed">
{`schemaVersion: "v1"
name: "${app.name}"
team: "${app.team}"
runtime: "${app.runtime}"
service:
  port: ${app.port}
  replicas: ${app.replicas}
  healthCheck:
    path: "/health"
    interval: 10s
git:
  repository: "${app.repository_url}"
  branch: "${app.branch}"
environments:
  ${app.environment}:
    autoDeploy: true`}
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
