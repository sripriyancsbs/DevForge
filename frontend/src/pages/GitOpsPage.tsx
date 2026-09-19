import React, { useState, useEffect, useRef, useId } from 'react';
import {
  GitBranch,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  FileCode,
  Server,
  Box,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  GitCommit,
  ArrowUpRight,
  Sliders,
  Check,
  Zap,
  Activity as ActivityIcon
} from 'lucide-react';
import { api } from '../services/api';
import {
  GitOpsApplication,
  GitOpsOperation,
  ArgoCDClusterStatus,
  Application
} from '../types';

export const GitOpsPage: React.FC = () => {
  const [gitopsApps, setGitopsApps] = useState<GitOpsApplication[]>([]);
  const [clusterStatus, setClusterStatus] = useState<ArgoCDClusterStatus | null>(null);
  const [allApps, setAllApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Enable modal state
  const [showEnableModal, setShowEnableModal] = useState(false);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>('');
  const [autoSync, setAutoSync] = useState(false);
  const [selfHeal, setSelfHeal] = useState(false);
  const [enableSubmitting, setEnableSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Selected app for inspecting live drift/manifest details
  const [selectedGitopsApp, setSelectedGitopsApp] = useState<GitOpsApplication | null>(null);

  // Operation tracking
  const [activeOps, setActiveOps] = useState<{ [appId: number]: string }>({});

  const pollIntervalRef = useRef<any>(null);

  const loadData = async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const [cluster, apps, rawApps] = await Promise.all([
        api.getGitOpsClusterStatus().catch(() => ({ available: false, version: 'unknown', server_url: '', namespace: 'argocd' })),
        api.listGitOpsApplications().catch(() => []),
        api.getApplications().catch(() => [])
      ]);

      setClusterStatus(cluster);
      setGitopsApps(apps);
      setAllApps(rawApps);

      // Keep selected app in sync
      if (selectedGitopsApp) {
        const found = apps.find(a => a.id === selectedGitopsApp.id);
        if (found) setSelectedGitopsApp(found);
      }
    } catch (err: any) {
      console.error('Failed to load GitOps data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();

    // Poll every 3 seconds to capture live reconciliation
    pollIntervalRef.current = setInterval(() => {
      loadData(true);
    }, 3000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Compute metrics
  const totalApps = gitopsApps.length;
  const syncedApps = gitopsApps.filter(a => a.sync_status === 'SYNCED').length;
  const outOfSyncApps = gitopsApps.filter(a => a.sync_status === 'OUT_OF_SYNC').length;
  const healthyApps = gitopsApps.filter(a => a.health_status === 'HEALTHY').length;

  // Unmanaged apps available for GitOps
  const managedAppIds = new Set(gitopsApps.map(g => g.application_id));
  const availableAppsToEnable = allApps.filter(a => !managedAppIds.has(a.id));

  const handleEnableGitOps = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) return;

    setEnableSubmitting(true);
    setActionError(null);

    try {
      await api.enableGitOps(Number(selectedAppId), {
        auto_sync: autoSync,
        self_heal: selfHeal,
        target_revision: 'main',
        namespace: 'devforge'
      });
      setShowEnableModal(false);
      setSelectedAppId('');
      await loadData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to enable GitOps');
    } finally {
      setEnableSubmitting(false);
    }
  };

  const handleSync = async (app: GitOpsApplication) => {
    setActiveOps(prev => ({ ...prev, [app.application_id]: 'SYNC' }));
    setActionError(null);
    try {
      await api.syncGitOpsApplication(app.application_id);
      await loadData(true);
    } catch (err: any) {
      setActionError(`Sync failed: ${err.message}`);
    } finally {
      setTimeout(() => {
        setActiveOps(prev => {
          const next = { ...prev };
          delete next[app.application_id];
          return next;
        });
      }, 2000);
    }
  };

  const handleRefresh = async (app: GitOpsApplication) => {
    setActiveOps(prev => ({ ...prev, [app.application_id]: 'REFRESH' }));
    setActionError(null);
    try {
      await api.refreshGitOpsApplication(app.application_id);
      await loadData(true);
    } catch (err: any) {
      setActionError(`Refresh failed: ${err.message}`);
    } finally {
      setTimeout(() => {
        setActiveOps(prev => {
          const next = { ...prev };
          delete next[app.application_id];
          return next;
        });
      }, 1500);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-emerald-400" />
              GitOps Continuous Delivery
            </h1>
            {clusterStatus?.available ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Argo CD {clusterStatus.version} Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                Argo CD Connecting...
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Declarative Kubernetes desired-state reconciliation powered by Argo CD and Kustomize.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadData()}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 border border-zinc-700 hover:border-zinc-500 rounded text-xs font-mono text-zinc-300 transition-colors"
          >
            <RotateCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            Refresh
          </button>

          {availableAppsToEnable.length > 0 && (
            <button
              onClick={() => setShowEnableModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium shadow-sm transition-colors"
            >
              <Zap className="w-3.5 h-3.5" />
              Enable GitOps
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="p-3 bg-red-950/60 border border-red-800/60 rounded text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Overview Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
            <span>ARGO CD CONTROLLER</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {clusterStatus?.available ? 'Connected' : 'Pending'}
          </div>
          <div className="text-[11px] font-mono text-zinc-500 mt-1">
            Namespace: {clusterStatus?.namespace || 'argocd'} • Port 8080
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
            <span>MANAGED APPLICATIONS</span>
            <Box className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {totalApps}
          </div>
          <div className="text-[11px] font-mono text-zinc-500 mt-1">
            {allApps.length} total IDP services provisioned
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
            <span>SYNCED / DESIRED STATE</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {syncedApps} / {totalApps || 1}
          </div>
          <div className="text-[11px] font-mono text-zinc-500 mt-1">
            Reconciled with Git revision HEAD
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
            <span>DRIFT DETECTED</span>
            <AlertCircle className={`w-4 h-4 ${outOfSyncApps > 0 ? 'text-amber-400' : 'text-zinc-500'}`} />
          </div>
          <div className={`text-xl font-bold font-mono ${outOfSyncApps > 0 ? 'text-amber-400' : 'text-zinc-400'}`}>
            {outOfSyncApps}
          </div>
          <div className="text-[11px] font-mono text-zinc-500 mt-1">
            {outOfSyncApps > 0 ? 'Cluster state differs from Git' : 'No resource drift'}
          </div>
        </div>
      </div>

      {/* Applications Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-wide text-zinc-200 uppercase font-mono">
            GitOps Applications ({gitopsApps.length})
          </h2>
        </div>

        {gitopsApps.length === 0 && !loading ? (
          <div className="p-8 border border-dashed border-zinc-800 rounded-lg text-center space-y-3">
            <GitBranch className="w-8 h-8 text-zinc-600 mx-auto" />
            <div className="text-sm text-zinc-300 font-medium">No GitOps Managed Applications Yet</div>
            <p className="text-xs text-zinc-500 max-w-md mx-auto">
              Enable GitOps for your provisioned applications to reconcile Kubernetes deployments directly from Git desired state.
            </p>
            {availableAppsToEnable.length > 0 && (
              <button
                onClick={() => setShowEnableModal(true)}
                className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium shadow-sm transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                Enable for Existing Application
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {gitopsApps.map((app) => {
              const isSyncing = app.sync_status === 'SYNCING' || activeOps[app.application_id] === 'SYNC';
              const isRefreshing = activeOps[app.application_id] === 'REFRESH';
              const isOutOfSync = app.sync_status === 'OUT_OF_SYNC';

              return (
                <div
                  key={app.id}
                  className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-5 transition-all hover:border-zinc-700 space-y-4"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-semibold text-sm text-white">{app.application_name}</span>
                        <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700/60">
                          {app.argocd_application_name}
                        </span>

                        {/* Sync Status Badge */}
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${
                            app.sync_status === 'SYNCED'
                              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                              : app.sync_status === 'OUT_OF_SYNC'
                              ? 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                              : app.sync_status === 'SYNCING'
                              ? 'bg-blue-950/60 text-blue-400 border-blue-800/60'
                              : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                          }`}
                        >
                          {app.sync_status === 'SYNCED' && <CheckCircle2 className="w-3 h-3" />}
                          {app.sync_status === 'OUT_OF_SYNC' && <AlertCircle className="w-3 h-3" />}
                          {app.sync_status === 'SYNCING' && <RefreshCw className="w-3 h-3 animate-spin" />}
                          {app.sync_status}
                        </span>

                        {/* Health Status Badge */}
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${
                            app.health_status === 'HEALTHY'
                              ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                              : app.health_status === 'PROGRESSING'
                              ? 'bg-blue-950/60 text-blue-400 border-blue-800/60'
                              : app.health_status === 'DEGRADED'
                              ? 'bg-red-950/60 text-red-400 border-red-800/60'
                              : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                          }`}
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-current" />
                          {app.health_status}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-zinc-400 font-mono flex-wrap">
                        <span>Repo: <span className="text-zinc-300">{app.git_repository}</span></span>
                        <span>Path: <span className="text-zinc-300">{app.git_path}</span></span>
                        <span>Revision: <span className="text-zinc-300">{app.target_revision}</span></span>
                        <span>Namespace: <span className="text-zinc-300">{app.namespace}</span></span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleSync(app)}
                        disabled={isSyncing}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors ${
                          isOutOfSync
                            ? 'bg-amber-600 hover:bg-amber-500 text-white font-semibold'
                            : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700'
                        }`}
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-emerald-400' : ''}`} />
                        {isSyncing ? 'Syncing...' : 'Sync'}
                      </button>

                      <button
                        onClick={() => handleRefresh(app)}
                        disabled={isRefreshing}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 rounded text-xs font-mono transition-colors"
                      >
                        <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
                        Refresh
                      </button>

                      <a
                        href={app.git_repository}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 hover:text-white rounded transition-colors"
                        title="View Git Repository"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>

                  {/* Drift Alert Banner */}
                  {isOutOfSync && (
                    <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded text-xs text-amber-300 space-y-2">
                      <div className="flex items-center gap-2 font-semibold">
                        <AlertCircle className="w-4 h-4 text-amber-400" />
                        <span>Live State Drift Detected: Application does not match Git repository desired state</span>
                      </div>
                      {app.drifted_resources && app.drifted_resources.length > 0 && (
                        <div className="pl-6 space-y-1 font-mono text-[11px] text-amber-400/90">
                          {app.drifted_resources.map((r, idx) => (
                            <div key={idx}>
                              • {r.kind} <span className="text-white">{r.name}</span> in namespace <span className="text-white">{r.namespace}</span> (Status: OutOfSync)
                            </div>
                          ))}
                        </div>
                      )}
                      <p className="pl-6 text-[11px] text-amber-400/70">
                        Click "Sync" to reconcile cluster actual state with Git repository manifests.
                      </p>
                    </div>
                  )}

                  {/* Operational Status Footer */}
                  <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] font-mono text-zinc-500 flex-wrap gap-2">
                    <div className="flex items-center gap-4">
                      <span>Last sync: {app.last_synced_at ? new Date(app.last_synced_at).toLocaleString() : 'Never'}</span>
                      {app.last_sync_revision && (
                        <span>Commit: {app.last_sync_revision.substring(0, 7)}</span>
                      )}
                      {app.auto_sync_enabled && (
                        <span className="text-emerald-400">Automated Sync: Enabled</span>
                      )}
                      {app.self_heal_enabled && (
                        <span className="text-emerald-400">Self-Heal: Enabled</span>
                      )}
                    </div>

                    {app.sync_message && (
                      <span className="text-zinc-400 max-w-md truncate" title={app.sync_message}>
                        {app.sync_message}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Enable GitOps Modal */}
      {showEnableModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg max-w-lg w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-emerald-400" />
                Enable GitOps via Argo CD
              </h3>
              <button
                onClick={() => setShowEnableModal(false)}
                className="text-zinc-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEnableGitOps} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-zinc-400">Application</label>
                <select
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value ? Number(e.target.value) : '')}
                  required
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="">-- Select an application --</option>
                  {availableAppsToEnable.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name} ({app.slug})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 pt-2 border-t border-zinc-800">
                <label className="text-xs font-mono text-zinc-400">Sync Behavior</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoSync}
                      onChange={(e) => setAutoSync(e.target.checked)}
                      className="rounded bg-zinc-800 border-zinc-700 text-emerald-500 focus:ring-0"
                    />
                    <span>Automated Synchronization (reconcile automatically when Git changes)</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selfHeal}
                      onChange={(e) => setSelfHeal(e.target.checked)}
                      className="rounded bg-zinc-800 border-zinc-700 text-emerald-500 focus:ring-0"
                    />
                    <span>Automated Self-Healing (revert manual drift automatically)</span>
                  </label>
                </div>
              </div>

              <div className="p-3 bg-zinc-800/50 rounded border border-zinc-700/60 text-[11px] text-zinc-400 space-y-1 font-mono">
                <div>• Manifest repo: https://github.com/sripriyancsbs/DevForge</div>
                <div>• Git path: gitops/applications/&lt;app&gt;/overlays/development</div>
                <div>• Target namespace: devforge</div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEnableModal(false)}
                  className="px-3 py-1.5 text-xs text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedAppId || enableSubmitting}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-medium shadow-sm transition-colors flex items-center gap-2"
                >
                  {enableSubmitting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                  {enableSubmitting ? 'Configuring GitOps...' : 'Confirm & Enable'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
