import React, { useState, useEffect } from 'react';
import {
  Activity,
  Server,
  Database,
  Cpu,
  Radio,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
  Terminal,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import {
  SystemHealthData,
  MetricsSummaryData,
  MonitoredService,
  AlertRule,
  ScrapeTarget,
} from '../types';
import { api } from '../services/api';

export const MonitoringPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummaryData | null>(null);
  const [services, setServices] = useState<MonitoredService[]>([]);
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  const [targets, setTargets] = useState<ScrapeTarget[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'services' | 'targets' | 'alerts'>('services');

  const loadAll = async () => {
    try {
      const [h, m, s, a, t] = await Promise.all([
        api.getSystemHealth().catch(() => null),
        api.getMetricsSummary().catch(() => null),
        api.getMonitoredServices().catch(() => []),
        api.getAlertRules().catch(() => []),
        api.getScrapeTargets().catch(() => []),
      ]);
      setHealth(h);
      setMetrics(m);
      setServices(s);
      setAlerts(a);
      setTargets(t);
    } catch (err) {
      console.error('Failed to load observability data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = () => {
    setRefreshing(true);
    loadAll();
  };

  const getStatusBadge = (status: string, idPrefix?: string) => {
    const s = (status || '').toLowerCase();
    const idAttr = idPrefix ? { id: `${idPrefix}-status-badge` } : {};
    if (s === 'healthy' || s === 'up' || s === 'connected') {
      return (
        <span
          {...idAttr}
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
        >
          <CheckCircle2 className="w-3 h-3" />
          HEALTHY
        </span>
      );
    }
    if (s === 'degraded' || s === 'warning' || s === 'pending') {
      return (
        <span
          {...idAttr}
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30"
        >
          <Clock className="w-3 h-3" />
          DEGRADED
        </span>
      );
    }
    return (
      <span
        {...idAttr}
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30"
      >
        <AlertCircle className="w-3 h-3" />
        OFFLINE
      </span>
    );
  };

  const prometheusUrl = health?.prometheus?.url || 'http://localhost:9090';
  const grafanaUrl = health?.grafana?.dashboard_url || 'http://localhost:3001';

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0">
      {/* Header & Direct External Monitoring Links */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-zinc-800/80 gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold tracking-tight text-white font-mono">
              Observability & Platform Monitoring
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time telemetry, Prometheus scrape targets, system health, and Grafana analytics.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            id="btn-refresh-monitoring"
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-mono font-medium border border-zinc-800 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <a
            id="btn-open-prometheus"
            href={prometheusUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white text-xs font-mono font-semibold border border-zinc-700 transition"
          >
            <Radio className="w-3.5 h-3.5 text-orange-400" />
            <span>Prometheus (9090)</span>
            <ExternalLink className="w-3 h-3 text-zinc-400" />
          </a>

          <a
            id="btn-open-grafana"
            href={grafanaUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-orange-600/20 hover:bg-orange-600/30 text-orange-300 hover:text-orange-200 text-xs font-mono font-semibold border border-orange-500/40 transition"
          >
            <Zap className="w-3.5 h-3.5 text-orange-400" />
            <span>Grafana Dashboard (3001)</span>
            <ExternalLink className="w-3 h-3 text-orange-400" />
          </a>
        </div>
      </div>

      {/* System Health Cards Grid */}
      <div id="monitoring-health-section" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 font-mono flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Core Component Health
          </h2>
          <span className="text-[11px] font-mono text-zinc-500">
            Scraped live via Prometheus & Platform Probes
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {/* Backend Card */}
          <div
            id="health-card-backend"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Server className="w-3.5 h-3.5 text-emerald-400" />
                Backend API
              </div>
              {getStatusBadge(health?.backend?.status || 'unknown', 'backend')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Port: :{health?.backend?.port ?? 8000}</div>
              <div>Uptime: {health?.backend?.uptime_seconds ?? '-'}s</div>
              <div>Env: {health?.backend?.environment ?? 'dev'}</div>
            </div>
          </div>

          {/* Worker Card */}
          <div
            id="health-card-worker"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                Worker
              </div>
              {getStatusBadge(health?.worker?.status || 'unknown', 'worker')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Active Jobs: {health?.worker?.active_jobs ?? 0}</div>
              <div>Metrics: :{health?.worker?.metrics_port ?? 8001}</div>
              <div>Heartbeat: {health?.worker?.heartbeat_seconds_ago !== null && health?.worker?.heartbeat_seconds_ago !== undefined ? `${health.worker.heartbeat_seconds_ago}s ago` : 'Live'}</div>
            </div>
          </div>

          {/* PostgreSQL Card */}
          <div
            id="health-card-database"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Database className="w-3.5 h-3.5 text-cyan-400" />
                PostgreSQL
              </div>
              {getStatusBadge(health?.database?.status || 'unknown', 'database')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Connections: {health?.database?.active_connections ?? 1}</div>
              <div>Engine: {health?.database?.engine ?? 'PostgreSQL 16'}</div>
              <div>Latency: {health?.database?.latency_ms ?? '-'}ms</div>
            </div>
          </div>

          {/* Kubernetes Card */}
          <div
            id="health-card-kubernetes"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                Kubernetes
              </div>
              {getStatusBadge(health?.kubernetes?.status || 'unknown', 'kubernetes')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Cluster: {health?.kubernetes?.cluster_name ?? 'kind-devforge'}</div>
              <div>Namespace: {health?.kubernetes?.namespace ?? 'devforge'}</div>
              <div>Nodes: {health?.kubernetes?.nodes_count ?? 1}</div>
            </div>
          </div>

          {/* Prometheus Card */}
          <div
            id="health-card-prometheus"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Radio className="w-3.5 h-3.5 text-orange-400" />
                Prometheus
              </div>
              {getStatusBadge(health?.prometheus?.status || 'unknown', 'prometheus')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Targets: {health?.prometheus?.active_targets ?? 4} UP</div>
              <div>Interval: {health?.prometheus?.scrape_interval ?? '5s'}</div>
              <div>Port: :9090</div>
            </div>
          </div>

          {/* Grafana Card */}
          <div
            id="health-card-grafana"
            className="p-3.5 rounded border border-zinc-800 bg-[#121215] font-mono flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-semibold">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Grafana
              </div>
              {getStatusBadge(health?.grafana?.status || 'unknown', 'grafana')}
            </div>
            <div className="mt-2.5 pt-2 border-t border-zinc-800/80 text-[11px] text-zinc-400 space-y-0.5">
              <div>Version: {health?.grafana?.version ?? '10.4.1'}</div>
              <div>Port: :3001</div>
              <div>Provisioned: Yes</div>
            </div>
          </div>
        </div>
      </div>

      {/* Operational Metrics Cards */}
      <div id="monitoring-metrics-section" className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 font-mono flex items-center gap-2">
          <Activity className="w-4 h-4 text-zinc-400" />
          Platform Operational Metrics
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
          <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
            <span className="text-zinc-500 text-[11px] uppercase">API Total Requests</span>
            <div className="text-2xl font-bold text-white mt-1" id="metric-api-requests">
              {(metrics?.api?.total_requests ?? 0).toLocaleString()}
            </div>
            <div className="text-[11px] text-emerald-400 mt-1">
              Active In-Flight: {metrics?.api?.active_requests ?? 0}
            </div>
          </div>

          <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
            <span className="text-zinc-500 text-[11px] uppercase">API Error Rate</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1" id="metric-api-errors">
              {metrics?.api?.error_rate_percent ?? 0.0}%
            </div>
            <div className="text-[11px] text-zinc-400 mt-1">
              Total 4xx/5xx: {metrics?.api?.total_errors ?? 0}
            </div>
          </div>

          <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
            <span className="text-zinc-500 text-[11px] uppercase">Provisioning Success</span>
            <div className="text-2xl font-bold text-white mt-1" id="metric-prov-success">
              {metrics?.provisioning?.success_rate_percent ?? 100}%
            </div>
            <div className="text-[11px] text-zinc-400 mt-1">
              {metrics?.provisioning?.succeeded ?? 0} / {metrics?.provisioning?.total_jobs ?? 0} Completed
            </div>
          </div>

          <div className="p-4 rounded border border-zinc-800 bg-[#121215]">
            <span className="text-zinc-500 text-[11px] uppercase">Ansible Automation</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1" id="metric-ansible-success">
              {metrics?.ansible?.success_rate_percent ?? 100}%
            </div>
            <div className="text-[11px] text-zinc-400 mt-1">
              {metrics?.ansible?.succeeded ?? 0} / {metrics?.ansible?.total_executions ?? 0} Executions
            </div>
          </div>
        </div>
      </div>

      {/* Tabs for Services, Scrape Targets, and Alerts */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden" id="monitoring-details-container">
        <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between bg-[#0e0e11]">
          <div className="flex items-center space-x-1 font-mono text-xs">
            <button
              id="tab-services"
              onClick={() => setActiveTab('services')}
              className={`px-3 py-1.5 rounded transition ${
                activeTab === 'services'
                  ? 'bg-zinc-800 text-white font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Services ({services.length})
            </button>
            <button
              id="tab-targets"
              onClick={() => setActiveTab('targets')}
              className={`px-3 py-1.5 rounded transition ${
                activeTab === 'targets'
                  ? 'bg-zinc-800 text-white font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Prometheus Targets ({targets.length})
            </button>
            <button
              id="tab-alerts"
              onClick={() => setActiveTab('alerts')}
              className={`px-3 py-1.5 rounded transition ${
                activeTab === 'alerts'
                  ? 'bg-zinc-800 text-white font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Alert Rules ({alerts.length})
            </button>
          </div>
          <span className="text-[11px] font-mono text-zinc-500 hidden sm:inline">
            Auto-refresh 10s
          </span>
        </div>

        {/* Tab 1: Monitored Services */}
        {activeTab === 'services' && (
          <div className="overflow-x-auto" id="monitoring-services-table">
            <table className="w-full text-left text-xs font-mono min-w-[640px] lg:min-w-full">
              <thead className="bg-[#09090b] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Service</th>
                  <th className="py-2.5 px-4 font-medium">Tier</th>
                  <th className="py-2.5 px-4 font-medium">Endpoint</th>
                  <th className="py-2.5 px-4 font-medium">Port</th>
                  <th className="py-2.5 px-4 font-medium">Latency</th>
                  <th className="py-2.5 px-4 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {services.map((svc) => (
                  <tr key={svc.name} className="hover:bg-zinc-800/30 transition">
                    <td className="py-3 px-4 font-semibold text-white">
                      <div>{svc.name}</div>
                      <div className="text-[11px] text-zinc-500 font-normal">{svc.description}</div>
                    </td>
                    <td className="py-3 px-4 text-zinc-400">{svc.tier}</td>
                    <td className="py-3 px-4 text-zinc-300 truncate max-w-xs">{svc.endpoint}</td>
                    <td className="py-3 px-4 text-zinc-400">:{svc.port}</td>
                    <td className="py-3 px-4 text-zinc-300">{svc.latency_ms ?? '-'} ms</td>
                    <td className="py-3 px-4 text-right">
                      {getStatusBadge(svc.health)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 2: Prometheus Targets */}
        {activeTab === 'targets' && (
          <div className="overflow-x-auto" id="monitoring-targets-table">
            <table className="w-full text-left text-xs font-mono min-w-[600px] lg:min-w-full">
              <thead className="bg-[#09090b] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Job</th>
                  <th className="py-2.5 px-4 font-medium">Scrape Target</th>
                  <th className="py-2.5 px-4 font-medium">Scrape URL</th>
                  <th className="py-2.5 px-4 font-medium">Last Scrape</th>
                  <th className="py-2.5 px-4 font-medium text-right">Health</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {targets.map((tgt, i) => (
                  <tr key={i} className="hover:bg-zinc-800/30 transition">
                    <td className="py-3 px-4 font-semibold text-white">{tgt.job}</td>
                    <td className="py-3 px-4 text-zinc-300">{tgt.instance}</td>
                    <td className="py-3 px-4 text-zinc-400 truncate max-w-xs">{tgt.scrape_url}</td>
                    <td className="py-3 px-4 text-zinc-400">
                      {tgt.last_scrape ? new Date(tgt.last_scrape).toLocaleTimeString() : 'Pending'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {getStatusBadge(tgt.health)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Alert Rules */}
        {activeTab === 'alerts' && (
          <div className="overflow-x-auto" id="monitoring-alerts-table">
            <table className="w-full text-left text-xs font-mono min-w-[640px] lg:min-w-full">
              <thead className="bg-[#09090b] border-b border-zinc-800 text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Alert Rule</th>
                  <th className="py-2.5 px-4 font-medium">Severity</th>
                  <th className="py-2.5 px-4 font-medium">Query Expression</th>
                  <th className="py-2.5 px-4 font-medium">Description</th>
                  <th className="py-2.5 px-4 font-medium text-right">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {alerts.map((alt) => (
                  <tr key={alt.name} className="hover:bg-zinc-800/30 transition">
                    <td className="py-3 px-4 font-semibold text-white">{alt.name}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                        alt.severity === 'critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {alt.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-400 font-mono text-[11px] max-w-xs truncate">{alt.expression}</td>
                    <td className="py-3 px-4 text-zinc-300 max-w-sm">{alt.description}</td>
                    <td className="py-3 px-4 text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                        alt.state === 'firing' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      }`}>
                        {alt.state}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
