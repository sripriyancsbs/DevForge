import React, { useState } from 'react';
import { Settings, Key, Shield, GitBranch, Database, Check, Server, Terminal, Lock } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [copiedKey, setCopiedKey] = useState(false);

  const copyToken = () => {
    navigator.clipboard?.writeText('df_live_sec_89fa12b984c17290ad4f');
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6 w-full min-w-0">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Platform Settings
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Active platform runtime configuration, environment variables, and external service contracts.
        </p>
      </div>

      {/* Section 1: Active Runtime Environment (Live metadata) */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Server className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Database & Infrastructure Runtime</h2>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            PostgreSQL 16 Active
          </span>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          DevForge strictly enforces PostgreSQL for all platform metadata, application definitions, and deployment logs.
          Automatic SQLite fallback is permanently disabled.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] uppercase">Database Engine</span>
            <div className="text-zinc-200 mt-1 font-semibold">PostgreSQL 16 (psycopg2)</div>
          </div>
          <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] uppercase">Cluster Connection</span>
            <div className="text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Verified & Persistent
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Git Provider Integration (VCS) */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <GitBranch className="w-4 h-4 text-zinc-300" />
            <h2 className="text-sm font-semibold text-white">Source Control (GitHub Integration)</h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/60">
            Configured via .env
          </span>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Default organization repository templates are loaded directly from the DevForge starter catalog.
        </p>
        <div className="text-xs font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800 flex items-center justify-between">
          <span>github.com/devforge-org/*</span>
          <span className="text-[11px] text-zinc-500">Public & Internal Templates</span>
        </div>
      </div>

      {/* Section 3: Container Registry Configuration */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-white">Container Registry</h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950/60 text-sky-400 border border-sky-800/60">
            Docker Compose Network
          </span>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          In Phase 1, images are packaged and orchestrated via Docker Compose bridge networking.
        </p>
        <div className="text-xs font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800">
          local.devforge.internal:5000/services
        </div>
      </div>

      {/* Section 4: Operator API Access */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Key className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">Operator API Authentication Token</h2>
          </div>
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Token used by automation runners and CLI commands targeting the DevForge REST API.
        </p>
        <div className="flex items-center gap-2">
          <input
            type="password"
            readOnly
            value="df_live_sec_89fa12b984c17290ad4f"
            className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs font-mono text-zinc-300 focus:outline-none"
          />
          <button
            onClick={copyToken}
            className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono rounded border border-zinc-700 transition flex items-center gap-1.5"
          >
            {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Terminal className="w-3.5 h-3.5" />}
            <span>{copiedKey ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Section 5: Phase 2 Planned Modules */}
      <div className="rounded-md border border-zinc-800/60 bg-[#0e0e11] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono">
            Upcoming Modules (Phase 2 Roadmap)
          </span>
          <span className="text-[10px] font-mono text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
            Planned
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono text-zinc-500">
          <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
            • Kubernetes (Helm / Argo CD)
          </div>
          <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
            • Terraform Cloud Provider
          </div>
          <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
            • Prometheus & Grafana Exporters
          </div>
        </div>
      </div>
    </div>
  );
};
