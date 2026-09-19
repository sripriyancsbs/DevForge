import React, { useState } from 'react';
import {
  GitCommit,
  Clock,
  Box,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Terminal,
  Filter,
  Play,
  RotateCcw,
  X
} from 'lucide-react';
import { Deployment } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';

interface DeploymentsPageProps {
  deployments: Deployment[];
  loading: boolean;
  onRefresh: () => void;
}

export const DeploymentsPage: React.FC<DeploymentsPageProps> = ({
  deployments,
  loading,
  onRefresh
}) => {
  const [selectedEnv, setSelectedEnv] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [activeLogDeployment, setActiveLogDeployment] = useState<Deployment | null>(null);

  const filtered = deployments.filter((d) => {
    const matchEnv = selectedEnv === 'all' || d.environment.toLowerCase() === selectedEnv.toLowerCase();
    const matchStatus = selectedStatus === 'all' || d.status.toLowerCase() === selectedStatus.toLowerCase();
    return matchEnv && matchStatus;
  });

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Deployments
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Audit trail of CI/CD builds, rolling container updates, and platform release logs.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3 p-3 rounded-md border border-zinc-800 bg-[#121215] text-xs">
        <span className="text-zinc-400 font-mono flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5" />
          <span>Filters:</span>
        </span>

        <select
          value={selectedEnv}
          onChange={(e) => setSelectedEnv(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none"
        >
          <option value="all">All Environments</option>
          <option value="production">Production</option>
          <option value="staging">Staging</option>
          <option value="development">Development</option>
          <option value="preview">Preview</option>
        </select>

        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none"
        >
          <option value="all">All Statuses</option>
          <option value="healthy">Healthy</option>
          <option value="deploying">Deploying</option>
          <option value="failed">Failed</option>
          <option value="rolled_back">Rolled Back</option>
        </select>
      </div>

      {/* Deployments Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[760px] lg:min-w-full">
            <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] font-mono uppercase text-zinc-400">
              <tr>
                <th className="py-2.5 px-4 font-medium">Application</th>
                <th className="py-2.5 px-4 font-medium">Release</th>
                <th className="py-2.5 px-4 font-medium">Commit & Message</th>
                <th className="py-2.5 px-4 font-medium">Environment</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
                <th className="py-2.5 px-4 font-medium">Triggered By</th>
                <th className="py-2.5 px-4 font-medium">Duration</th>
                <th className="py-2.5 px-4 font-medium text-right">Logs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-500">
                    No matching deployment records found.
                  </td>
                </tr>
              ) : (
                filtered.map((dep) => (
                  <tr key={dep.id} className="hover:bg-zinc-800/40 transition">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <Box className="w-3.5 h-3.5 text-zinc-500" />
                      <span>{dep.application_name}</span>
                    </td>
                    <td className="py-3 px-4 text-zinc-200">{dep.version}</td>
                    <td className="py-3 px-4 max-w-xs truncate text-zinc-400">
                      <span className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300 mr-2 text-[11px]">
                        {dep.commit_hash}
                      </span>
                      <span>{dep.commit_message || 'Standard release'}</span>
                    </td>
                    <td className="py-3 px-4 capitalize text-zinc-300">{dep.environment}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={dep.status} />
                    </td>
                    <td className="py-3 px-4 text-zinc-400">{dep.triggered_by}</td>
                    <td className="py-3 px-4 text-zinc-400">{dep.duration}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setActiveLogDeployment(dep)}
                        className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 text-[11px] inline-flex items-center gap-1.5 transition"
                      >
                        <Terminal className="w-3 h-3 text-emerald-400" />
                        <span>Logs</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Build Logs Modal */}
      {activeLogDeployment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl bg-[#0c0c0e] border border-zinc-800 rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
            <div className="p-3 border-b border-zinc-800 flex items-center justify-between bg-[#121215]">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span className="font-semibold text-white">
                  {activeLogDeployment.application_name} ({activeLogDeployment.version})
                </span>
                <span className="text-zinc-500">[{activeLogDeployment.commit_hash}]</span>
              </div>
              <button
                onClick={() => setActiveLogDeployment(null)}
                className="text-zinc-400 hover:text-white p-1 rounded hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 bg-zinc-950 max-h-96 overflow-y-auto">
              <pre className="text-xs font-mono text-zinc-300 leading-relaxed">
                {activeLogDeployment.logs ||
                  `[00:00:01] Fetching container tag ${activeLogDeployment.version}\n[00:00:15] Synthesized deployment manifest\n[00:00:32] Applying rolling rollout\n[00:00:48] All 4 pods healthy on target cluster.`}
              </pre>
            </div>
            <div className="p-3 border-t border-zinc-800 bg-[#121215] flex justify-end">
              <button
                onClick={() => setActiveLogDeployment(null)}
                className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono rounded"
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
