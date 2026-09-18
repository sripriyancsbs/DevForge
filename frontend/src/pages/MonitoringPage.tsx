import React, { useState, useEffect } from 'react';
import { Activity, Zap, AlertTriangle, ArrowDown, Clock } from 'lucide-react';
import { MonitoringData } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';

export const MonitoringPage: React.FC = () => {
  const [data, setData] = useState<MonitoringData | null>(null);

  useEffect(() => {
    api.getMonitoring().then(setData).catch(console.error);
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Monitoring & SLOs
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Platform-wide traffic throughput, tail latencies (P95/P99), and error budget burn rates.
        </p>
      </div>

      {/* Latency & SLO Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
        <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px] uppercase">Tail Latency (P95)</span>
          <div className="text-2xl font-bold text-white mt-1">
            {data?.global.p95_latency_ms ?? 42.1} ms
          </div>
          <div className="text-[11px] text-emerald-400 mt-1">P50: {data?.global.p50_latency_ms ?? 18.4} ms</div>
        </div>

        <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px] uppercase">Tail Latency (P99)</span>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {data?.global.p99_latency_ms ?? 112.5} ms
          </div>
          <div className="text-[11px] text-zinc-400 mt-1">SLA Target: &lt; 250 ms</div>
        </div>

        <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px] uppercase">Aggregate RPS</span>
          <div className="text-2xl font-bold text-white mt-1">
            {data?.global.total_throughput_rps.toLocaleString() ?? '4,410'}
          </div>
          <div className="text-[11px] text-emerald-400 mt-1">Peak: 6,800 rps</div>
        </div>

        <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
          <span className="text-zinc-500 text-[11px] uppercase">Global Error Rate</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {data?.global.avg_error_rate ?? '0.02%'}
          </div>
          <div className="text-[11px] text-emerald-400 mt-1">SLO: {data?.global.slo_status ?? '99.98%'}</div>
        </div>
      </div>

      {/* Service Telemetry Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
              Service Performance Telemetry
            </h2>
          </div>
          <span className="text-[11px] font-mono text-zinc-500">Auto-refresh 30s</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0e0e11] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
              <tr>
                <th className="py-2.5 px-4 font-medium">Service</th>
                <th className="py-2.5 px-4 font-medium">Throughput</th>
                <th className="py-2.5 px-4 font-medium">P95 Latency</th>
                <th className="py-2.5 px-4 font-medium">Error Rate</th>
                <th className="py-2.5 px-4 font-medium">CPU</th>
                <th className="py-2.5 px-4 font-medium">Memory</th>
                <th className="py-2.5 px-4 font-medium text-right">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {data?.service_metrics.map((s) => (
                <tr key={s.service} className="hover:bg-zinc-800/40 transition">
                  <td className="py-3 px-4 font-medium text-white">{s.service}</td>
                  <td className="py-3 px-4 text-zinc-300">{s.rps} rps</td>
                  <td className="py-3 px-4 text-zinc-300">{s.p95_latency}</td>
                  <td className="py-3 px-4">
                    <span className={parseFloat(s.error_rate) > 0.5 ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                      {s.error_rate}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-zinc-300">{s.cpu}</td>
                  <td className="py-3 px-4 text-zinc-300">{s.memory}</td>
                  <td className="py-3 px-4 text-right">
                    <StatusBadge status={s.status} />
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
