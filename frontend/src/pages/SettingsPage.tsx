import React, { useState } from 'react';
import { Settings, Key, Shield, GitBranch, Database, Check, Save } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [apiKeySaved, setApiKeySaved] = useState(false);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Platform Settings
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Manage workspace authentication, Git VCS providers, container registries, and notifications.
        </p>
      </div>

      {/* Section 1: Git Integration */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <GitBranch className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Source Control (GitHub Integration)</h2>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-400 border border-emerald-800/40">
            Connected
          </span>
        </div>
        <p className="text-xs text-zinc-400">
          DevForge synchronizes repository webhook events to automatically register PR preview deployments and commit statuses.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] uppercase">Organization</span>
            <div className="text-zinc-200 mt-1">github.com/devforge-org</div>
          </div>
          <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] uppercase">Webhook Status</span>
            <div className="text-emerald-400 mt-1 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Active (200 OK)
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Container Registry */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-white">Container Registry</h2>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-sky-950/50 text-sky-400 border border-sky-800/40">
            Verified
          </span>
        </div>
        <p className="text-xs text-zinc-400">
          Registry endpoint used to store multi-arch container images generated during self-service app builds.
        </p>
        <div className="text-xs font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800">
          registry.devforge.internal/v2/services
        </div>
      </div>

      {/* Section 3: API Tokens */}
      <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Key className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">DevForge Platform API Token</h2>
          </div>
        </div>
        <p className="text-xs text-zinc-400">
          Token used by local CLI tools and external CI runners to interact with the DevForge API.
        </p>
        <div className="flex items-center gap-2">
          <input
            type="password"
            readOnly
            value="df_live_sec_89fa12b984c17290ad4f"
            className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs font-mono text-zinc-300 focus:outline-none"
          />
          <button
            onClick={() => {
              setApiKeySaved(true);
              setTimeout(() => setApiKeySaved(false), 2000);
            }}
            className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono rounded border border-zinc-700 transition flex items-center gap-1.5"
          >
            {apiKeySaved ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Save className="w-3.5 h-3.5" />}
            <span>{apiKeySaved ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
