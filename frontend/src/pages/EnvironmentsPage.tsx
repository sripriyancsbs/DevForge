import React from 'react';
import { Server, Globe, Cpu, HardDrive, CheckCircle2, AlertTriangle, ArrowUpRight } from 'lucide-react';
import { Environment } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';

interface EnvironmentsPageProps {
  environments: Environment[];
  loading: boolean;
  onSelectEnvironment?: (envName: string) => void;
}

export const EnvironmentsPage: React.FC<EnvironmentsPageProps> = ({
  environments,
  loading
}) => {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800/80">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Environments
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Cluster regions, deployed services, and resource allocations per deployment environment.
          </p>
        </div>
      </div>

      {/* Grid of Environments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {environments.map((env) => (
          <div
            key={env.id}
            className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4 hover:border-zinc-700 transition"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2.5">
                  <h2 className="text-base font-bold text-white font-mono">{env.name}</h2>
                  <StatusBadge status={env.status} />
                </div>
                <div className="text-xs font-mono text-zinc-400 mt-1 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-zinc-500" />
                  <span>{env.region}</span>
                </div>
              </div>
              <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded border border-zinc-700/60 uppercase">
                {env.type}
              </span>
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed">{env.description}</p>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-zinc-800/80 text-xs font-mono">
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/60">
                <div className="text-[10px] text-zinc-500 uppercase">Active Apps</div>
                <div className="text-sm font-bold text-zinc-100 mt-0.5">{env.services_count}</div>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/60">
                <div className="text-[10px] text-zinc-500 uppercase">CPU Allocated</div>
                <div className="text-[11px] font-bold text-zinc-100 mt-1 truncate">{env.cpu_allocated}</div>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/60">
                <div className="text-[10px] text-zinc-500 uppercase">Memory Used</div>
                <div className="text-[11px] font-bold text-zinc-100 mt-1 truncate">{env.memory_allocated}</div>
              </div>
            </div>

            <div className="pt-2 text-[11px] font-mono text-zinc-500 flex items-center justify-between border-t border-zinc-800/40">
              <span className="truncate">Endpoint: {env.cluster_endpoint}</span>
              <span className="text-emerald-400">Synced</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
