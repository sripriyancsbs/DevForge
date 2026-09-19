import React from 'react';
import {
  Box,
  CheckCircle2,
  GitCommit,
  AlertOctagon,
  Clock,
  ArrowRight,
  RefreshCw,
  Activity as ActivityIcon,
  Server,
  ArrowUpRight
} from 'lucide-react';
import { OverviewData } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';

interface OverviewPageProps {
  data: OverviewData | null;
  loading: boolean;
  onRefresh: () => void;
  onSelectApplication: (appName: string) => void;
  onNavigateTab: (tab: any) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  data,
  loading,
  onRefresh,
  onSelectApplication,
  onNavigateTab
}) => {
  if (loading && !data) {
    return (
      <div className="p-8 flex items-center justify-center text-zinc-500 font-mono text-xs">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        Loading platform telemetry...
      </div>
    );
  }

  const metrics = data?.metrics;
  const recentDeployments = data?.recent_deployments || [];
  const serviceHealth = data?.service_health || [];
  const recentActivity = data?.recent_activity || [];

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2 font-sans">
            Platform Overview
          </h1>
          <p className="text-xs text-zinc-400 mt-1 font-sans">
            Global status and operational telemetry across your DevForge platform. Select any application to manage its operations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-zinc-800 bg-[#121215] text-zinc-300 hover:text-white hover:border-zinc-700 text-xs font-mono transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
          <button
            onClick={() => onNavigateTab('create-application')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs transition shadow-xs font-sans"
          >
            <span>+ Create Application</span>
          </button>
        </div>
      </div>

      {/* 4 Truthful High-Signal Metric Cards (Requirement 17 & 18) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Total Applications */}
        <div
          onClick={() => onNavigateTab('applications')}
          className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between cursor-pointer hover:border-zinc-700 transition group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Applications</span>
            <Box className="w-4 h-4 text-zinc-500 group-hover:text-emerald-400 transition" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white tracking-tight">
              {metrics?.applications_count ?? 0}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] text-zinc-500">
              <span>Platform services</span>
              <span className="text-emerald-400 font-medium">Manage catalog →</span>
            </div>
          </div>
        </div>

        {/* Metric 2: Healthy Services */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Healthy Services</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white tracking-tight">
              {metrics?.healthy_services ?? '0 / 0 Healthy'}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] text-zinc-500">
              <span>Active health checks</span>
              <span className="text-zinc-400 font-medium">Verified live</span>
            </div>
          </div>
        </div>

        {/* Metric 3: Active Deployments */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Active Deployments</span>
            <GitCommit className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white tracking-tight">
              {metrics?.active_deployments ?? 0}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] text-zinc-500">
              <span>In-progress rollouts</span>
              <span className={metrics?.active_deployments ? 'text-sky-400' : 'text-zinc-400'}>
                {metrics?.active_deployments ? 'Pipeline active' : 'Idle'}
              </span>
            </div>
          </div>
        </div>

        {/* Metric 4: Failed Operations */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Failed Deployments</span>
            <AlertOctagon className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-3">
            <div className={`text-2xl font-bold tracking-tight ${metrics?.failed_deployments ? 'text-rose-400' : 'text-white'}`}>
              {metrics?.failed_deployments ?? 0}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] text-zinc-500">
              <span>Rollout alerts</span>
              <span className={metrics?.failed_deployments ? 'text-rose-400 font-medium' : 'text-zinc-400'}>
                {metrics?.failed_deployments ? 'Attention needed' : 'All clean'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Platform Deployments & Service Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Table 1: Recent Platform Deployments */}
        <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCommit className="w-4 h-4 text-zinc-400" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Recent Platform Deployments
              </h2>
            </div>
            <button
              onClick={() => onNavigateTab('applications')}
              className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition"
            >
              <span>Applications →</span>
            </button>
          </div>

          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Application</th>
                  <th className="py-2.5 px-4 font-medium">Version</th>
                  <th className="py-2.5 px-4 font-medium">Environment</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {recentDeployments.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-500">
                      No deployments recorded.
                    </td>
                  </tr>
                ) : (
                  recentDeployments.map((dep) => (
                    <tr
                      key={dep.id}
                      onClick={() => onSelectApplication(dep.application_name)}
                      className="hover:bg-zinc-800/40 cursor-pointer transition group"
                    >
                      <td className="py-2.5 px-4 font-medium text-white group-hover:text-emerald-400 transition">
                        {dep.application_name}
                      </td>
                      <td className="py-2.5 px-4 text-zinc-300">{dep.version}</td>
                      <td className="py-2.5 px-4 capitalize text-zinc-400">{dep.environment}</td>
                      <td className="py-2.5 px-4">
                        <StatusBadge status={dep.status} />
                      </td>
                      <td className="py-2.5 px-4 text-right text-zinc-500 text-[11px]">
                        {dep.created_at ? new Date(dep.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'recently'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Table 2: Service Health */}
        <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-zinc-400" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                Platform Service Health
              </h2>
            </div>
            <span className="text-[11px] text-zinc-500">
              Live Probes
            </span>
          </div>

          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Service</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">CPU</th>
                  <th className="py-2.5 px-4 font-medium">Memory</th>
                  <th className="py-2.5 px-4 font-medium text-right">RPS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {serviceHealth.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-500">
                      No service telemetry recorded.
                    </td>
                  </tr>
                ) : (
                  serviceHealth.slice(0, 6).map((svc) => (
                    <tr
                      key={svc.id}
                      onClick={() => onSelectApplication(svc.service_name)}
                      className="hover:bg-zinc-800/40 cursor-pointer transition group"
                    >
                      <td className="py-2.5 px-4 font-medium text-white group-hover:text-emerald-400 transition">
                        {svc.service_name}
                      </td>
                      <td className="py-2.5 px-4">
                        <StatusBadge status={svc.status} />
                      </td>
                      <td className="py-2.5 px-4 text-zinc-300">{svc.cpu_percent}%</td>
                      <td className="py-2.5 px-4 text-zinc-300">{svc.memory_mb}</td>
                      <td className="py-2.5 px-4 text-right text-zinc-400">{svc.requests_per_sec}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent Platform Activity */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
              Recent Platform Activity
            </h2>
          </div>
          <button
            onClick={() => onNavigateTab('activity')}
            className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition"
          >
            <span>Activity Audit Trail →</span>
          </button>
        </div>

        <div className="divide-y divide-zinc-800/60 text-xs">
          {recentActivity.length === 0 ? (
            <div className="p-6 text-center text-zinc-500">
              No recent platform activity.
            </div>
          ) : (
            recentActivity.slice(0, 5).map((act) => (
              <div
                key={act.id}
                onClick={() => onSelectApplication(act.target)}
                className="p-3.5 hover:bg-zinc-800/40 cursor-pointer flex items-center justify-between gap-3 transition group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                  <div>
                    <span className="font-semibold text-white group-hover:text-emerald-400 transition">
                      {act.action}
                    </span>
                    <span className="text-zinc-400 ml-2">
                      {act.details || act.target}
                    </span>
                  </div>
                </div>
                <span className="text-[11px] text-zinc-500 shrink-0">
                  {act.created_at ? new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
