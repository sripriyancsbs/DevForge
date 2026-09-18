import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Plus,
  Box,
  GitBranch,
  ExternalLink,
  RotateCcw,
  MoreVertical,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Layers
} from 'lucide-react';
import { Application } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';

interface ApplicationsPageProps {
  applications: Application[];
  loading: boolean;
  onSelectApplication: (appName: string) => void;
  onNavigateToCreate: () => void;
  onTriggerDeploy: (appId: number, version: string, env: string) => void;
}

export const ApplicationsPage: React.FC<ApplicationsPageProps> = ({
  applications,
  loading,
  onSelectApplication,
  onNavigateToCreate,
  onTriggerDeploy
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [envFilter, setEnvFilter] = useState('all');

  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      const matchesSearch =
        search === '' ||
        app.name.toLowerCase().includes(search.toLowerCase()) ||
        app.runtime.toLowerCase().includes(search.toLowerCase()) ||
        app.team.toLowerCase().includes(search.toLowerCase()) ||
        app.repository_url.toLowerCase().includes(search.toLowerCase());

      const matchesStatus =
        statusFilter === 'all' || app.status.toLowerCase() === statusFilter.toLowerCase();

      const matchesEnv =
        envFilter === 'all' || app.environment.toLowerCase() === envFilter.toLowerCase();

      return matchesSearch && matchesStatus && matchesEnv;
    });
  }, [applications, search, statusFilter, envFilter]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Applications
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            View and manage registered platform applications and their deployment state.
          </p>
        </div>
        <button
          onClick={onNavigateToCreate}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs transition shadow-xs self-start sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Create Application</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-md border border-zinc-800 bg-[#121215]">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by application name, team, runtime..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 font-mono"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          {/* Status filter */}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-[11px] font-mono text-zinc-500 hidden md:inline">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-600 font-mono"
            >
              <option value="all">All Statuses</option>
              <option value="healthy">Healthy</option>
              <option value="degraded">Degraded</option>
              <option value="failed">Failed</option>
              <option value="deploying">Deploying</option>
            </select>
          </div>

          {/* Environment filter */}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-[11px] font-mono text-zinc-500 hidden md:inline">Env:</span>
            <select
              value={envFilter}
              onChange={(e) => setEnvFilter(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-600 font-mono"
            >
              <option value="all">All Environments</option>
              <option value="production">Production</option>
              <option value="staging">Staging</option>
              <option value="development">Development</option>
              <option value="preview">Preview</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applications Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
              <tr>
                <th className="py-2.5 px-4 font-medium">Application</th>
                <th className="py-2.5 px-4 font-medium">Runtime</th>
                <th className="py-2.5 px-4 font-medium">Repository</th>
                <th className="py-2.5 px-4 font-medium">Environment</th>
                <th className="py-2.5 px-4 font-medium">Version</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
                <th className="py-2.5 px-4 font-medium">Last Deployment</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {loading && applications.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-500">
                    Loading applications...
                  </td>
                </tr>
              ) : filteredApps.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-500">
                    No applications matched your search filters.
                  </td>
                </tr>
              ) : (
                filteredApps.map((app) => (
                  <tr
                    key={app.id}
                    onClick={() => onSelectApplication(app.name)}
                    className="hover:bg-zinc-800/40 cursor-pointer transition group"
                  >
                    {/* Application Name & Team */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <Box className="w-4 h-4 text-zinc-500 group-hover:text-emerald-400 transition" />
                        <div>
                          <div className="font-medium text-white font-mono group-hover:text-emerald-400 transition">
                            {app.name}
                          </div>
                          <div className="text-[10px] text-zinc-500">{app.team}</div>
                        </div>
                      </div>
                    </td>

                    {/* Runtime */}
                    <td className="py-3 px-4 text-zinc-300">
                      <span className="bg-zinc-950 border border-zinc-800 px-2 py-0.5 rounded text-[11px]">
                        {app.runtime}
                      </span>
                    </td>

                    {/* Repository */}
                    <td className="py-3 px-4 text-zinc-400">
                      <a
                        href={app.repository_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="hover:text-zinc-200 inline-flex items-center gap-1 max-w-[160px] truncate"
                        title={app.repository_url}
                      >
                        <GitBranch className="w-3 h-3 shrink-0" />
                        <span className="truncate">{app.repository_url.replace('https://github.com/', '')}</span>
                      </a>
                    </td>

                    {/* Environment */}
                    <td className="py-3 px-4">
                      <span className="capitalize text-zinc-300">{app.environment}</span>
                    </td>

                    {/* Version */}
                    <td className="py-3 px-4 text-zinc-300">
                      <span className="bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700/60 text-zinc-200">
                        {app.version}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4">
                      <StatusBadge status={app.status} />
                    </td>

                    {/* Last Deployment */}
                    <td className="py-3 px-4 text-zinc-400 text-[11px]">
                      {app.last_deployment_at
                        ? new Date(app.last_deployment_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        : 'Never'}
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => onSelectApplication(app.name)}
                          className="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] border border-zinc-700 transition"
                        >
                          Inspect
                        </button>
                        <button
                          onClick={() => onTriggerDeploy(app.id, 'v' + (parseFloat(app.version.replace('v', '')) + 0.1).toFixed(1) + '.0', app.environment)}
                          className="p-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-400 border border-emerald-800/60 transition"
                          title="Trigger Quick Deploy"
                        >
                          <Play className="w-3 h-3 fill-current" />
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
  );
};
