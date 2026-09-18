import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Network, Database, Server, CheckCircle2 } from 'lucide-react';
import { InfrastructureData } from '../types';
import { api } from '../services/api';

export const InfrastructurePage: React.FC = () => {
  const [data, setData] = useState<InfrastructureData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getInfrastructure()
      .then(setData)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Infrastructure
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Connected compute nodes, Kubernetes clusters, managed datastores, and networking topology.
        </p>
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
          <span className="text-[11px] font-mono text-zinc-500">AWS EKS Integration</span>
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
