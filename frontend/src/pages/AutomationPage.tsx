import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Play,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  FileCode,
  Server,
  Box,
  Copy,
  Check
} from 'lucide-react';
import { api } from '../services/api';
import { AnsiblePlaybook, AnsibleExecution, Application } from '../types';

export const AutomationPage: React.FC = () => {
  const [playbooks, setPlaybooks] = useState<AnsiblePlaybook[]>([]);
  const [executions, setExecutions] = useState<AnsibleExecution[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedPlaybook, setSelectedPlaybook] = useState<string>('configure_environment');
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [selectedEnv, setSelectedEnv] = useState<string>('development');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Active Execution for Terminal Monitor
  const [activeExecution, setActiveExecution] = useState<AnsibleExecution | null>(null);
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);

  const pollTimerRef = useRef<any>(null);

  // Load initial data
  const loadData = async () => {
    try {
      const [pbList, execList, appList] = await Promise.all([
        api.getAnsiblePlaybooks().catch(() => []),
        api.listAnsibleExecutions().catch(() => []),
        api.getApplications().catch(() => [])
      ]);

      setPlaybooks(pbList);
      setExecutions(execList);
      setApplications(appList);

      // Default active execution to latest if none selected
      if (!activeExecution && execList.length > 0) {
        setActiveExecution(execList[0]);
      }
    } catch (err: any) {
      console.error('Failed to load automation data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  // Poll active execution if it is PENDING or RUNNING
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    if (activeExecution && (activeExecution.status === 'PENDING' || activeExecution.status === 'RUNNING')) {
      pollTimerRef.current = setInterval(async () => {
        try {
          const updated = await api.getAnsibleExecution(activeExecution.id);
          setActiveExecution(updated);
          // Refresh list as well
          const latestList = await api.listAnsibleExecutions();
          setExecutions(latestList);

          if (updated.status === 'SUCCESS' || updated.status === 'FAILED') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          }
        } catch (err) {
          console.error('Error polling execution status:', err);
        }
      }, 1500);
    }

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [activeExecution?.id, activeExecution?.status]);

  const handleRunPlaybook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlaybook) return;

    setSubmitting(true);
    setFormError(null);
    setActiveExecution(null);

    try {
      const appIdNum = selectedAppId ? parseInt(selectedAppId, 10) : undefined;
      const created = await api.createAnsibleExecution({
        playbook_name: selectedPlaybook,
        application_id: isNaN(appIdNum as any) ? undefined : appIdNum,
        environment_id: selectedEnv,
      });

      // Set immediately to the new execution to start polling
      setActiveExecution(created);
      const latestList = await api.listAnsibleExecutions().catch(() => []);
      setExecutions(latestList);
    } catch (err: any) {
      setFormError(err.message || 'Failed to start Ansible execution');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = async (executionId: number) => {
    setRetryingId(executionId);
    try {
      setActiveExecution(null);
      const retried = await api.retryAnsibleExecution(executionId);
      setActiveExecution(retried);
      await loadData();
    } catch (err: any) {
      console.error('Failed to retry execution:', err);
    } finally {
      setRetryingId(null);
    }
  };

  const handleCopyLogs = () => {
    const text = activeExecution?.output || activeExecution?.error_output || '';
    if (text && navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedLogs(true);
      setTimeout(() => setCopiedLogs(false), 2000);
    }
  };

  const getStatusBadge = (status: string, isMonitor: boolean = false) => {
    const idAttr = isMonitor ? { id: 'ansible-status-badge' } : {};
    switch (status) {
      case 'SUCCESS':
        return (
          <span
            {...idAttr}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            SUCCESS
          </span>
        );
      case 'RUNNING':
        return (
          <span
            {...idAttr}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30"
          >
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
            RUNNING
          </span>
        );
      case 'PENDING':
        return (
          <span
            {...idAttr}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30"
          >
            <Clock className="w-3.5 h-3.5 animate-pulse" />
            PENDING
          </span>
        );
      case 'FAILED':
        return (
          <span
            {...idAttr}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30"
          >
            <AlertCircle className="w-3.5 h-3.5" />
            FAILED
          </span>
        );
      default:
        return (
          <span
            {...idAttr}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700"
          >
            {status}
          </span>
        );
    }
  };

  const currentPlaybookMeta = playbooks.find((p) => p.name === selectedPlaybook);

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Automation
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Ansible configuration management, environment baseline orchestration, and automated health checks.
          </p>
        </div>

        <button
          id="ansible-refresh-btn"
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white transition text-xs font-mono border border-zinc-800 disabled:opacity-50 cursor-pointer"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-zinc-400' : ''}`} />
          <span>Sync</span>
        </button>
      </div>

      {/* Main Grid: Launcher + Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Playbook Launcher (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded-lg border border-zinc-800 bg-[#121215] shadow-sm overflow-hidden" id="ansible-launcher-section">
            <div className="px-4 py-3 border-b border-zinc-800/80 bg-[#0d0d10] flex items-center gap-2">
              <Layers className="w-4 h-4 text-zinc-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200 font-mono">
                Execute Playbook
              </h2>
            </div>

            <form onSubmit={handleRunPlaybook} className="p-4 space-y-4">
              {formError && (
                <div className="p-2.5 bg-red-950/40 border border-red-800/60 rounded text-xs text-red-300 font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
                  <span className="break-all">{formError}</span>
                </div>
              )}

              {/* Playbook Selection */}
              <div className="space-y-1.5 font-mono text-xs">
                <label className="text-zinc-400 font-semibold block uppercase text-[11px]">
                  Playbook
                </label>
                <select
                  id="ansible-playbook-select"
                  value={selectedPlaybook}
                  onChange={(e) => setSelectedPlaybook(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-zinc-600 font-mono"
                >
                  {playbooks.map((pb) => (
                    <option key={pb.name} value={pb.name}>
                      {pb.title} ({pb.name})
                    </option>
                  ))}
                </select>
                {currentPlaybookMeta && (
                  <p className="text-[11px] text-zinc-500 leading-relaxed pt-0.5">
                    {currentPlaybookMeta.description}
                  </p>
                )}
              </div>

              {/* Application Selection */}
              <div className="space-y-1.5 font-mono text-xs">
                <label className="text-zinc-400 font-semibold block uppercase text-[11px]">
                  Target Application
                </label>
                <select
                  id="ansible-app-select"
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-zinc-600 font-mono"
                >
                  <option value="">-- None (Environment / Baseline) --</option>
                  {applications.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name} (#{app.id} - {app.runtime || 'service'})
                    </option>
                  ))}
                </select>
              </div>

              {/* Environment Selection */}
              <div className="space-y-1.5 font-mono text-xs">
                <label className="text-zinc-400 font-semibold block uppercase text-[11px]">
                  Environment
                </label>
                <select
                  id="ansible-env-select"
                  value={selectedEnv}
                  onChange={(e) => setSelectedEnv(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs focus:outline-none focus:border-zinc-600 font-mono"
                >
                  <option value="development">Development (Local)</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                </select>
              </div>

              {/* Run Button */}
              <button
                type="submit"
                id="ansible-run-btn"
                disabled={submitting || !selectedPlaybook}
                className="w-full py-2.5 px-4 rounded bg-zinc-800 hover:bg-zinc-700 text-white font-mono text-xs font-semibold flex items-center justify-center gap-2 border border-zinc-700 transition shadow-sm disabled:opacity-50 cursor-pointer"
              >
                <Play className={`w-3.5 h-3.5 ${submitting ? 'animate-spin' : 'fill-current'}`} />
                <span>{submitting ? 'Queueing...' : 'Run Playbook'}</span>
              </button>
            </form>
          </div>
        </div>

        {/* Live Execution Terminal & Details (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="rounded-lg border border-zinc-800 bg-[#121215] shadow-sm overflow-hidden" id="ansible-monitor-section">
            <div className="px-5 py-3.5 border-b border-zinc-800/80 bg-[#0d0d10] flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <Terminal className="w-4 h-4 text-zinc-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-200 font-mono">
                  Execution Output
                </h2>
                {activeExecution && (
                  <span className="text-zinc-400 text-xs font-mono" id="ansible-exec-id">
                    #{activeExecution.id}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {activeExecution && (
                  <>
                    {getStatusBadge(activeExecution.status, true)}

                    <button
                      id="ansible-copy-output-btn"
                      onClick={handleCopyLogs}
                      title="Copy output"
                      className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 text-xs font-mono border border-zinc-800 transition"
                    >
                      {copiedLogs ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedLogs ? 'Copied' : 'Copy'}</span>
                    </button>

                    <button
                      id="ansible-retry-btn"
                      onClick={() => handleRetry(activeExecution.id)}
                      disabled={retryingId === activeExecution.id || activeExecution.status === 'RUNNING'}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white transition text-xs font-mono font-semibold border border-zinc-700 disabled:opacity-50 cursor-pointer"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${retryingId === activeExecution.id ? 'animate-spin' : ''}`} />
                      <span>Retry</span>
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Execution Metadata Bar */}
            {activeExecution ? (
              <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono bg-[#0f0f13] border-b border-zinc-800/80">
                <div>
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Playbook</span>
                  <span id="ansible-exec-playbook" className="text-zinc-200 font-semibold mt-0.5 block truncate">
                    {activeExecution.playbook_name}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Target</span>
                  <span id="ansible-exec-target" className="text-zinc-300 mt-0.5 block truncate">
                    {activeExecution.application_name || `env:${activeExecution.environment_id}`}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Duration</span>
                  <span id="ansible-exec-duration" className="text-zinc-300 mt-0.5 block">
                    {activeExecution.duration_seconds !== null && activeExecution.duration_seconds !== undefined
                      ? `${activeExecution.duration_seconds}s`
                      : activeExecution.status === 'RUNNING'
                      ? 'In progress...'
                      : '-'}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px] uppercase font-semibold">Return Code</span>
                  <span
                    id="ansible-exec-rc"
                    className={`font-semibold mt-0.5 block ${
                      activeExecution.return_code === 0
                        ? 'text-emerald-400'
                        : activeExecution.return_code !== null
                        ? 'text-red-400'
                        : 'text-zinc-400'
                    }`}
                  >
                    {activeExecution.return_code !== null ? `rc=${activeExecution.return_code}` : '-'}
                  </span>
                </div>
              </div>
            ) : null}

            {/* Monospace Output Terminal */}
            <div className="p-4 bg-[#09090b]">
              <pre
                id="ansible-terminal-output"
                className="p-3.5 rounded bg-black/60 border border-zinc-800 text-[11px] text-zinc-300 font-mono overflow-x-auto max-h-96 min-h-[14rem] whitespace-pre-wrap leading-relaxed select-text"
              >
                {activeExecution?.output || activeExecution?.error_output || (
                  <span className="text-zinc-600 italic">
                    {activeExecution
                      ? `Execution #${activeExecution.id} (${activeExecution.status}). Awaiting output...`
                      : 'No execution selected. Select or start a playbook to view execution output.'}
                  </span>
                )}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* Execution History Table */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md overflow-hidden" id="ansible-history-section">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-zinc-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-200 font-mono">
              Ansible Execution History
            </h2>
          </div>
          <span className="text-[11px] text-zinc-400 font-mono">
            {executions.length} recorded executions
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono min-w-[700px] lg:min-w-full" id="ansible-executions-table">
            <thead className="bg-[#09090b] text-zinc-400 border-b border-zinc-800">
              <tr>
                <th className="px-4 py-2.5 font-medium">Run ID</th>
                <th className="px-4 py-2.5 font-medium">Playbook</th>
                <th className="px-4 py-2.5 font-medium">Target</th>
                <th className="px-4 py-2.5 font-medium">Environment</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Duration</th>
                <th className="px-4 py-2.5 font-medium">Completed</th>
                <th className="px-4 py-2.5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {executions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-zinc-500 italic">
                    No Ansible executions recorded yet.
                  </td>
                </tr>
              ) : (
                executions.map((exec) => (
                  <tr
                    key={exec.id}
                    className={`hover:bg-zinc-900/40 transition cursor-pointer ${
                      activeExecution?.id === exec.id ? 'bg-zinc-900/60' : ''
                    }`}
                    onClick={() => setActiveExecution(exec)}
                  >
                    <td className="px-4 py-3 text-zinc-200 font-bold">#{exec.id}</td>
                    <td className="px-4 py-3 text-zinc-200 font-semibold">{exec.playbook_name}</td>
                    <td className="px-4 py-3 text-zinc-300">
                      {exec.application_name || 'System / Baseline'}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">{exec.environment_id}</td>
                    <td className="px-4 py-3">{getStatusBadge(exec.status)}</td>
                    <td className="px-4 py-3 text-zinc-400">
                      {exec.duration_seconds !== null && exec.duration_seconds !== undefined
                        ? `${exec.duration_seconds}s`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {exec.completed_at ? new Date(exec.completed_at).toLocaleTimeString() : 'In Progress'}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveExecution(exec);
                        }}
                        className="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800"
                      >
                        View
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRetry(exec.id);
                        }}
                        disabled={retryingId === exec.id || exec.status === 'RUNNING'}
                        className="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 disabled:opacity-50"
                      >
                        Retry
                      </button>
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
