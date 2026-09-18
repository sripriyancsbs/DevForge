import React from 'react';
import {
  Box,
  CheckCircle2,
  GitCommit,
  AlertOctagon,
  Clock,
  ArrowUpRight,
  RefreshCw,
  Cpu,
  Layers,
  Terminal,
  Activity as ActivityIcon
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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Overview
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Manage applications, deployments, environments, and infrastructure.
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
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs transition shadow-xs"
          >
            <span>+ Create Application</span>
          </button>
        </div>
      </div>

      {/* 4 High-Signal Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Applications */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-400 font-medium">Applications</span>
            <Box className="w-4 h-4 text-zinc-500" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {metrics?.applications_count ?? 8}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] font-mono text-zinc-500">
              <span>Registered services</span>
              <span className="text-emerald-400 font-semibold">+2 this week</span>
            </div>
          </div>
        </div>

        {/* Metric 2: Healthy Services */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-400 font-medium">Healthy Services</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {metrics?.healthy_services ?? '5 / 6 Healthy'}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] font-mono text-zinc-500">
              <span>Healthchecks passing</span>
              <span className="text-emerald-400 font-semibold">99.8%</span>
            </div>
          </div>
        </div>

        {/* Metric 3: Active Deployments */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-400 font-medium">Active Deployments</span>
            <GitCommit className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">
              {metrics?.active_deployments ?? 1}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] font-mono text-zinc-500">
              <span>Running rollouts</span>
              <span className="text-sky-400 font-semibold">In pipeline</span>
            </div>
          </div>
        </div>

        {/* Metric 4: Failed Deployments */}
        <div className="p-4 rounded-md border border-zinc-800 bg-[#121215] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-400 font-medium">Failed Deployments</span>
            <AlertOctagon className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-rose-400 tracking-tight">
              {metrics?.failed_deployments ?? 1}
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] font-mono text-zinc-500">
              <span>Last 24 hours</span>
              <span className="text-rose-400 font-semibold">Attention needed</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Deployments & Service Health */}
      <div className="space-y-6">
        {/* Table 1: Recent Deployments */}
        <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCommit className="w-4 h-4 text-zinc-400" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                Recent Deployments
              </h2>
            </div>
            <button
              onClick={() => onNavigateTab('deployments')}
              className="text-xs text-zinc-400 hover:text-white font-mono flex items-center gap-1 transition"
            >
              <span>View all</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Application</th>
                  <th className="py-2.5 px-4 font-medium">Version</th>
                  <th className="py-2.5 px-4 font-medium">Environment</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">Duration</th>
                  <th className="py-2.5 px-4 font-medium text-right">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 font-mono">
                {recentDeployments.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-zinc-500">
                      No deployments recorded.
                    </td>
                  </tr>
                ) : (
                  recentDeployments.map((dep) => (
                    <tr
                      key={dep.id}
                      onClick={() => onSelectApplication(dep.application_name)}
                      className="hover:bg-zinc-800/40 cursor-pointer transition"
                    >
                      <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                        <Box className="w-3.5 h-3.5 text-zinc-500" />
                        <span>{dep.application_name}</span>
                      </td>
                      <td className="py-3 px-4 text-zinc-300">
                        <span className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300 border border-zinc-700/60">
                          {dep.version}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-zinc-300 capitalize">{dep.environment}</span>
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={dep.status} />
                      </td>
                      <td className="py-3 px-4 text-zinc-400">{dep.duration}</td>
                      <td className="py-3 px-4 text-right text-zinc-500">
                        {new Date(dep.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Two-column section: Service Health and Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Table 2: Service Health (2/3 width on desktop) */}
          <div className="lg:col-span-2 border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ActivityIcon className="w-4 h-4 text-zinc-400" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                  Service Health
                </h2>
              </div>
              <span className="text-[11px] font-mono text-zinc-500">Real-time telemetry</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Service</th>
                    <th className="py-2.5 px-4 font-medium">Status</th>
                    <th className="py-2.5 px-4 font-medium">CPU</th>
                    <th className="py-2.5 px-4 font-medium">Memory</th>
                    <th className="py-2.5 px-4 font-medium">Requests</th>
                    <th className="py-2.5 px-4 font-medium text-right">Error Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 font-mono">
                  {serviceHealth.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-zinc-500">
                        No health probes registered.
                      </td>
                    </tr>
                  ) : (
                    serviceHealth.map((svc) => (
                      <tr
                        key={svc.id}
                        onClick={() => onSelectApplication(svc.service_name)}
                        className="hover:bg-zinc-800/40 cursor-pointer transition"
                      >
                        <td className="py-3 px-4 font-medium text-white">{svc.service_name}</td>
                        <td className="py-3 px-4">
                          <StatusBadge status={svc.status} />
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={
                              svc.cpu_percent > 70
                                ? 'text-amber-400 font-bold'
                                : 'text-zinc-300'
                            }
                          >
                            {svc.cpu_percent}%
                          </span>
                        </td>
                        <td className="py-3 px-4 text-zinc-300">{svc.memory_mb}</td>
                        <td className="py-3 px-4 text-zinc-300">{svc.requests_per_sec} rps</td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={
                              parseFloat(svc.error_rate) > 0.5
                                ? 'text-rose-400 font-bold'
                                : 'text-emerald-400'
                            }
                          >
                            {svc.error_rate}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Compact Section: Recent Activity (1/3 width on desktop) */}
          <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-400" />
                <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                  Recent Activity
                </h2>
              </div>
              <button
                onClick={() => onNavigateTab('activity')}
                className="text-xs text-zinc-400 hover:text-white font-mono flex items-center gap-1 transition"
              >
                <span>Audit</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="p-3 divide-y divide-zinc-800/50 flex-1 overflow-y-auto max-h-96">
              {recentActivity.length === 0 ? (
                <div className="py-6 text-center text-xs text-zinc-500 font-mono">
                  No activity events recorded.
                </div>
              ) : (
                recentActivity.map((act) => (
                  <div key={act.id} className="py-2.5 first:pt-1 last:pb-1 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-zinc-200">{act.action}</span>
                      <span className="text-[10px] text-zinc-500 font-mono">
                        {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-400 font-mono truncate">
                      <span className="text-zinc-300 font-medium">{act.target}</span>
                      {act.details && <span className="text-zinc-500"> — {act.details}</span>}
                    </div>
                    <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                      by <span className="text-zinc-400">{act.actor}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
