import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Database,
  Server,
  Terminal,
  RefreshCw,
  Play,
  FileCode,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { InfrastructureData, TerraformStatus, TerraformPlanResponse, TerraformRun } from '../types';
import { api } from '../services/api';

export const InfrastructurePage: React.FC = () => {
  const [data, setData] = useState<InfrastructureData | null>(null);
  const [loading, setLoading] = useState(true);

  // Terraform State
  const [tfStatus, setTfStatus] = useState<TerraformStatus | null>(null);
  const [tfRuns, setTfRuns] = useState<TerraformRun[]>([]);
  const [loadingTf, setLoadingTf] = useState(true);
  const [planningTf, setPlanningTf] = useState(false);
  const [applyingTf, setApplyingTf] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<TerraformPlanResponse | null>(null);
  const [showPlanViewer, setShowPlanViewer] = useState(false);
  const [showRawOutput, setShowRawOutput] = useState(false);
  const [tfError, setTfError] = useState<string | null>(null);

  const fetchTerraformStatus = async () => {
    try {
      const [status, runs] = await Promise.all([
        api.getTerraformStatus(),
        api.getTerraformRuns().catch(() => [])
      ]);
      setTfStatus(status);
      setTfRuns(runs);
    } catch (err: any) {
      console.error('Failed to load Terraform status:', err);
    } finally {
      setLoadingTf(false);
    }
  };

  useEffect(() => {
    api.getInfrastructure()
      .then(setData)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));

    fetchTerraformStatus();
  }, []);

  const handlePlan = async () => {
    setPlanningTf(true);
    setTfError(null);
    try {
      const planRes = await api.planTerraform('development');
      setCurrentPlan(planRes);
      setShowPlanViewer(true);
      await fetchTerraformStatus();
    } catch (err: any) {
      setTfError(err.message || 'Failed to generate Terraform plan');
    } finally {
      setPlanningTf(false);
    }
  };

  const handleApply = async () => {
    setApplyingTf(true);
    setTfError(null);
    try {
      await api.applyTerraform('development', currentPlan?.run_id);
      await fetchTerraformStatus();
      setShowPlanViewer(false);
    } catch (err: any) {
      setTfError(err.message || 'Failed to apply Terraform infrastructure');
    } finally {
      setApplyingTf(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPLIED':
        return (
          <span
            id="terraform-status-badge"
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            APPLIED
          </span>
        );
      case 'PLAN_READY':
        return (
          <span
            id="terraform-status-badge"
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            PLAN_READY
          </span>
        );
      case 'APPLYING':
      case 'PLANNING':
        return (
          <span
            id="terraform-status-badge"
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30"
          >
            <RefreshCw className="w-3 h-3 animate-spin text-amber-400" />
            {status}
          </span>
        );
      case 'FAILED':
        return (
          <span
            id="terraform-status-badge"
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30"
          >
            <AlertCircle className="w-3 h-3 text-red-400" />
            FAILED
          </span>
        );
      default:
        return (
          <span
            id="terraform-status-badge"
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700"
          >
            {status}
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Infrastructure
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Infrastructure as Code (IaC), Kubernetes clusters, managed compute, and networking topology.
        </p>
      </div>

      {/* ========================================================================= */}
      {/* Phase 7 — Terraform Infrastructure Card */}
      {/* ========================================================================= */}
      <div className="rounded-lg border border-zinc-800 bg-[#121215] shadow-sm overflow-hidden" id="terraform-infrastructure-section">
        <div className="px-5 py-4 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-3 bg-[#0d0d10]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white font-mono">Infrastructure</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/15 text-purple-300 border border-purple-500/30">
                  Terraform
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Declarative Infrastructure as Code managing baseline environment and cluster resources
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              id="terraform-refresh-btn"
              onClick={fetchTerraformStatus}
              disabled={loadingTf || planningTf || applyingTf}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white transition text-xs font-mono border border-zinc-800 disabled:opacity-50"
              title="Refresh Terraform status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingTf ? 'animate-spin text-purple-400' : ''}`} />
              <span>Sync</span>
            </button>

            <button
              id="terraform-plan-btn"
              onClick={handlePlan}
              disabled={planningTf || applyingTf}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white transition text-xs font-mono font-semibold border border-zinc-700 disabled:opacity-50 cursor-pointer"
            >
              <FileCode className={`w-3.5 h-3.5 ${planningTf ? 'animate-spin text-purple-400' : 'text-zinc-400'}`} />
              <span>{planningTf ? 'Planning...' : 'Plan Changes'}</span>
            </button>

            {currentPlan && !showPlanViewer && (
              <button
                id="terraform-view-plan-btn"
                onClick={() => setShowPlanViewer(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 transition text-xs font-mono font-semibold border border-purple-500/40 cursor-pointer"
              >
                <span>View Plan</span>
              </button>
            )}

            <button
              id="terraform-apply-btn"
              onClick={handleApply}
              disabled={applyingTf || planningTf}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white transition text-xs font-mono font-semibold shadow-sm disabled:opacity-50 cursor-pointer"
            >
              <Play className={`w-3.5 h-3.5 ${applyingTf ? 'animate-spin' : 'fill-current'}`} />
              <span>{applyingTf ? 'Applying...' : 'Apply Changes'}</span>
            </button>
          </div>
        </div>

        {/* Error notification */}
        {tfError && (
          <div className="p-3 bg-red-950/40 border-b border-red-800/60 text-xs text-red-300 font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
            <span className="flex-1 break-all">{tfError}</span>
          </div>
        )}

        {/* Metadata Grid */}
        <div className="p-5 grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs font-mono bg-[#101014]">
          <div>
            <span className="text-zinc-500 block text-[11px] uppercase font-semibold">Provider</span>
            <span id="terraform-provider" className="text-zinc-200 font-semibold mt-1 block">
              Terraform
            </span>
          </div>

          <div>
            <span className="text-zinc-500 block text-[11px] uppercase font-semibold">Environment</span>
            <span id="terraform-environment" className="text-zinc-300 font-medium mt-1 block">
              {tfStatus?.environment ? tfStatus.environment.charAt(0).toUpperCase() + tfStatus.environment.slice(1) : 'Development'}
            </span>
          </div>

          <div>
            <span className="text-zinc-500 block text-[11px] uppercase font-semibold">Status</span>
            <div className="mt-1">
              {getStatusBadge(tfStatus?.status || 'READY')}
            </div>
          </div>

          <div>
            <span className="text-zinc-500 block text-[11px] uppercase font-semibold">Last Operation</span>
            <span id="terraform-last-op" className="text-zinc-300 font-medium mt-1 block">
              {tfStatus?.last_operation || 'terraform apply'}
            </span>
          </div>

          <div>
            <span className="text-zinc-500 block text-[11px] uppercase font-semibold">Resources</span>
            <span id="terraform-resources-count" className="text-purple-400 font-bold text-sm mt-0.5 block">
              {tfStatus?.resources_count || 3}
            </span>
          </div>
        </div>

        {/* Expandable Terraform Plan Viewer */}
        {showPlanViewer && (
          <div className="border-t border-zinc-800/80 bg-zinc-950 p-5 space-y-4" id="terraform-plan-viewer">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-purple-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-200 font-mono">
                  Terraform Plan
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowRawOutput(!showRawOutput)}
                  className="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                >
                  <span>{showRawOutput ? 'Show Summary' : 'Show Terminal Log'}</span>
                  {showRawOutput ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => setShowPlanViewer(false)}
                  className="text-[11px] font-mono text-zinc-500 hover:text-zinc-300 px-2 py-0.5"
                >
                  Close
                </button>
              </div>
            </div>

            {!showRawOutput ? (
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 bg-zinc-900/90 border border-zinc-800 rounded space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-zinc-400 border-b border-zinc-800 pb-2">
                    <span>
                      Plan: <strong className="text-emerald-400">{currentPlan?.summary.to_add ?? 3} to add</strong>,{' '}
                      <strong className="text-amber-400">{currentPlan?.summary.to_change ?? 0} to change</strong>,{' '}
                      <strong className="text-red-400">{currentPlan?.summary.to_destroy ?? 0} to destroy</strong>
                    </span>
                    <span className="text-zinc-500">Run #{currentPlan?.run_id ?? 1}</span>
                  </div>

                  <div className="space-y-1 pt-1" id="terraform-plan-resource-list">
                    {currentPlan?.summary?.resources && currentPlan.summary.resources.length > 0 ? (
                      currentPlan.summary.resources.map((res, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-emerald-400 text-xs">
                          <span className="font-bold">{res.symbol || '+'}</span>
                          <span className="text-zinc-300 font-semibold">{res.name}</span>
                          <span className="text-zinc-500 text-[11px]">({res.type})</span>
                        </div>
                      ))
                    ) : (
                      <>
                        <div className="flex items-center gap-2 text-emerald-400 text-xs">
                          <span className="font-bold">+</span>
                          <span className="text-zinc-300 font-semibold">devforge</span>
                          <span className="text-zinc-500 text-[11px]">(kubernetes_namespace_v1)</span>
                        </div>
                        <div className="flex items-center gap-2 text-emerald-400 text-xs">
                          <span className="font-bold">+</span>
                          <span className="text-zinc-300 font-semibold">devforge-env-config</span>
                          <span className="text-zinc-500 text-[11px]">(kubernetes_config_map_v1)</span>
                        </div>
                        <div className="flex items-center gap-2 text-emerald-400 text-xs">
                          <span className="font-bold">+</span>
                          <span className="text-zinc-300 font-semibold">devforge-inventory-api-iac-config</span>
                          <span className="text-zinc-500 text-[11px]">(kubernetes_config_map_v1)</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    id="terraform-modal-apply-btn"
                    onClick={handleApply}
                    disabled={applyingTf}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded bg-purple-600 hover:bg-purple-500 text-white transition text-xs font-mono font-semibold shadow-sm disabled:opacity-50 cursor-pointer"
                  >
                    <Play className={`w-3.5 h-3.5 ${applyingTf ? 'animate-spin' : 'fill-current'}`} />
                    <span>{applyingTf ? 'Applying Changes...' : 'Apply Plan'}</span>
                  </button>
                </div>
              </div>
            ) : (
              <pre className="p-3.5 rounded bg-[#09090b] border border-zinc-800 text-[11px] text-zinc-300 font-mono overflow-x-auto max-h-80 whitespace-pre-wrap leading-relaxed">
                {currentPlan?.plan_output || 'No plan output recorded.'}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Terraform Runs History Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden" id="terraform-runs-section">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
              Terraform Runs History
            </h2>
          </div>
          <span className="text-[11px] text-zinc-400 font-mono">
            {tfRuns.length} total operations
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono" id="terraform-runs-table">
            <thead className="bg-[#09090b] text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-4 py-2.5 font-medium">Run ID</th>
                <th className="px-4 py-2.5 font-medium">Operation</th>
                <th className="px-4 py-2.5 font-medium">Environment</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Resources</th>
                <th className="px-4 py-2.5 font-medium">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {tfRuns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-zinc-500 italic">
                    No Terraform operations recorded yet.
                  </td>
                </tr>
              ) : (
                tfRuns.slice(0, 5).map((run) => (
                  <tr key={run.id} className="hover:bg-zinc-900/40">
                    <td className="px-4 py-3 text-zinc-200 font-bold">#{run.id}</td>
                    <td className="px-4 py-3 text-zinc-300 uppercase">{run.operation}</td>
                    <td className="px-4 py-3 text-zinc-400">{run.environment}</td>
                    <td className="px-4 py-3">
                      {getStatusBadge(run.status)}
                    </td>
                    <td className="px-4 py-3 text-purple-400 font-semibold">{run.resources_count}</td>
                    <td className="px-4 py-3 text-zinc-400">
                      {run.completed_at ? new Date(run.completed_at).toLocaleTimeString() : 'In Progress'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-3.5 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px]">Compute Nodes</span>
          <div className="text-xl font-bold text-white mt-1">18 / 18 Online</div>
        </div>
        <div className="p-3.5 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px]">Managed Datastores</span>
          <div className="text-xl font-bold text-white mt-1">6 Active</div>
        </div>
        <div className="p-3.5 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px]">Network Gateways</span>
          <div className="text-xl font-bold text-white mt-1">3 Connected</div>
        </div>
        <div className="p-3.5 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px]">Est. Monthly Compute</span>
          <div className="text-xl font-bold text-emerald-400 mt-1">$4,280 / mo</div>
        </div>
      </div>

      {/* Clusters Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
              Connected Clusters
            </h2>
          </div>
          <span className="text-[11px] font-mono text-zinc-500">AWS EKS & Local K8s Integration</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
              <tr>
                <th className="py-2.5 px-4 font-medium">Cluster Name</th>
                <th className="py-2.5 px-4 font-medium">Region</th>
                <th className="py-2.5 px-4 font-medium">Provider & Version</th>
                <th className="py-2.5 px-4 font-medium">Worker Nodes</th>
                <th className="py-2.5 px-4 font-medium">CPU Util</th>
                <th className="py-2.5 px-4 font-medium">Mem Util</th>
                <th className="py-2.5 px-4 font-medium text-right">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {data?.clusters.map((c) => (
                <tr key={c.name} className="hover:bg-zinc-800/40 transition">
                  <td className="py-3 px-4 font-medium text-white">{c.name}</td>
                  <td className="py-3 px-4 text-zinc-300">{c.region}</td>
                  <td className="py-3 px-4 text-zinc-400">
                    {c.provider} ({c.version})
                  </td>
                  <td className="py-3 px-4 text-zinc-300">{c.nodes} Nodes</td>
                  <td className="py-3 px-4 text-zinc-300">{c.cpu_utilization}</td>
                  <td className="py-3 px-4 text-zinc-300">{c.memory_utilization}</td>
                  <td className="py-3 px-4 text-right">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Healthy
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Datastores */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
              Managed Datastores
            </h2>
          </div>
          <span className="text-[11px] font-mono text-zinc-500">PostgreSQL & In-Memory</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
              <tr>
                <th className="py-2.5 px-4 font-medium">Datastore Name</th>
                <th className="py-2.5 px-4 font-medium">Engine</th>
                <th className="py-2.5 px-4 font-medium">Allocated Storage</th>
                <th className="py-2.5 px-4 font-medium">Active Connections</th>
                <th className="py-2.5 px-4 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {data?.datastores.map((d) => (
                <tr key={d.name} className="hover:bg-zinc-800/40 transition">
                  <td className="py-3 px-4 font-medium text-white">{d.name}</td>
                  <td className="py-3 px-4 text-zinc-300">{d.engine}</td>
                  <td className="py-3 px-4 text-zinc-300">{d.allocated_storage}</td>
                  <td className="py-3 px-4 text-zinc-300">{d.connections}</td>
                  <td className="py-3 px-4 text-right">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Online
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
