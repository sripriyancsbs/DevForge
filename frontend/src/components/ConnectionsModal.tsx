import React, { useState, useEffect } from 'react';
import {
  Github,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  X,
  Server,
  Database,
  ArrowRight,
  ShieldCheck,
  Zap,
  Globe
} from 'lucide-react';
import {
  getIntegrationsState,
  verifyAndSaveGitHubToken,
  verifyAndSaveVercelToken,
  disconnectGitHub,
  disconnectVercel,
  setCompletedConnectionsOnboarding,
  DEFAULT_GITHUB_TOKEN,
  DEFAULT_GITHUB_OWNER,
  IntegrationsState
} from '../services/integrationsService';

interface ConnectionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export const ConnectionsModal: React.FC<ConnectionsModalProps> = ({ isOpen, onClose, onSaved }) => {
  const [integrations, setIntegrations] = useState<IntegrationsState>(getIntegrationsState());
  const [activeTab, setActiveTab] = useState<'github' | 'vercel' | 'database'>('github');

  // GitHub input
  const [ghToken, setGhToken] = useState(integrations.github.token || '');
  const [ghLoading, setGhLoading] = useState(false);
  const [ghError, setGhError] = useState<string | null>(null);
  const [ghSuccess, setGhSuccess] = useState<string | null>(null);

  // Vercel input
  const [vToken, setVToken] = useState(integrations.vercel.token || '');
  const [vTeamId, setVTeamId] = useState(integrations.vercel.teamId || '');
  const [vLoading, setVLoading] = useState(false);
  const [vError, setVError] = useState<string | null>(null);
  const [vSuccess, setVSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const state = getIntegrationsState();
      setIntegrations(state);
      setGhToken(state.github.token || '');
      setVToken(state.vercel.token || '');
      setVTeamId(state.vercel.teamId || '');
      setGhError(null);
      setGhSuccess(null);
      setVError(null);
      setVSuccess(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConnectGitHub = async (tokenToUse?: string) => {
    const token = tokenToUse || ghToken;
    if (!token.trim()) {
      setGhError('Please enter a GitHub Personal Access Token.');
      return;
    }
    setGhLoading(true);
    setGhError(null);
    setGhSuccess(null);

    const res = await verifyAndSaveGitHubToken(token);
    setGhLoading(false);
    if (res.success && res.user) {
      setGhSuccess(`Successfully connected as @${res.user.login}!`);
      setIntegrations(getIntegrationsState());
    } else {
      setGhError(res.error || 'Failed to authenticate with GitHub.');
    }
  };

  const handleDisconnectGitHub = () => {
    disconnectGitHub();
    setGhToken('');
    setGhSuccess(null);
    setGhError(null);
    setIntegrations(getIntegrationsState());
  };

  const handleConnectVercel = async () => {
    if (!vToken.trim()) {
      setVError('Please enter a Vercel Access Token.');
      return;
    }
    setVLoading(true);
    setVError(null);
    setVSuccess(null);

    const res = await verifyAndSaveVercelToken(vToken, vTeamId);
    setVLoading(false);
    if (res.success && res.user) {
      setVSuccess(`Successfully connected to Vercel account (${res.user.username})!`);
      setIntegrations(getIntegrationsState());
    } else {
      setVError(res.error || 'Failed to authenticate with Vercel.');
    }
  };

  const handleDisconnectVercel = () => {
    disconnectVercel();
    setVToken('');
    setVSuccess(null);
    setVError(null);
    setIntegrations(getIntegrationsState());
  };

  const handleDone = () => {
    setCompletedConnectionsOnboarding(true);
    if (onSaved) onSaved();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#121215] border border-zinc-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800/80 flex items-center justify-between bg-zinc-900/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white font-mono flex items-center gap-2">
                <span>Platform Integrations & Connections</span>
              </h2>
              <p className="text-xs text-zinc-400">
                Connect your developer accounts to provision real repositories and live cloud deployments.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-2 rounded-lg hover:bg-zinc-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-zinc-800/80 px-6 bg-zinc-950/60 gap-4 text-xs font-mono">
          <button
            onClick={() => setActiveTab('github')}
            className={`py-3 px-1 border-b-2 font-medium flex items-center gap-2 transition ${
              activeTab === 'github'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Github className="w-4 h-4" />
            <span>GitHub Repository</span>
            {integrations.github.connected && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('vercel')}
            className={`py-3 px-1 border-b-2 font-medium flex items-center gap-2 transition ${
              activeTab === 'vercel'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Vercel Hosting</span>
            {integrations.vercel.connected && (
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('database')}
            className={`py-3 px-1 border-b-2 font-medium flex items-center gap-2 transition ${
              activeTab === 'database'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Neon Database</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* TAB 1: GITHUB */}
          {activeTab === 'github' && (
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white font-mono flex items-center gap-2">
                    <Github className="w-4 h-4 text-emerald-400" />
                    <span>GitHub Account Integration</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    When you create an application, DevForge creates the project repository in your account and pushes the scaffolded code.
                  </p>
                </div>
                {integrations.github.connected ? (
                  <span className="px-2.5 py-1 bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-[11px] font-mono rounded-full flex items-center gap-1.5 shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Connected</span>
                  </span>
                ) : (
                  <span className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 text-zinc-400 text-[11px] font-mono rounded-full shrink-0">
                    Not Connected
                  </span>
                )}
              </div>

              {integrations.github.connected && integrations.github.user && (
                <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <img
                      src={integrations.github.user.avatar_url}
                      alt={integrations.github.user.login}
                      className="w-10 h-10 rounded-full border border-zinc-700"
                    />
                    <div>
                      <div className="text-sm font-semibold text-white font-mono flex items-center gap-2">
                        <span>{integrations.github.user.name}</span>
                        <span className="text-xs text-zinc-400 font-normal">(@{integrations.github.user.login})</span>
                      </div>
                      <a
                        href={integrations.github.user.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-emerald-400 hover:underline flex items-center gap-1 mt-0.5"
                      >
                        <span>View profile on GitHub</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                  <button
                    onClick={handleDisconnectGitHub}
                    className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition"
                  >
                    Disconnect
                  </button>
                </div>
              )}

              {/* Status alerts */}
              {ghError && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2 font-mono">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{ghError}</span>
                </div>
              )}
              {ghSuccess && (
                <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{ghSuccess}</span>
                </div>
              )}

              {/* Token input */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-300 font-mono flex items-center justify-between">
                  <span>GitHub Personal Access Token (classic or fine-grained)</span>
                  <a
                    href="https://github.com/settings/tokens/new?scopes=repo,read:user,user:email&description=DevForge-IDP"
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center gap-1"
                  >
                    <span>Generate token</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder="ghp_... or gho_... (requires 'repo' scope)"
                    value={ghToken}
                    onChange={(e) => setGhToken(e.target.value)}
                    className="flex-1 px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 font-mono placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    onClick={() => handleConnectGitHub()}
                    disabled={ghLoading}
                    className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 transition shrink-0"
                  >
                    {ghLoading ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying...</span>
                      </>
                    ) : (
                      <>
                        <span>Test & Connect</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
                <p className="text-[11px] text-zinc-500">
                  DevForge requires the <code>repo</code> scope to create new repositories and push template files.
                </p>
              </div>

              {/* Quick connect default token */}
              {DEFAULT_GITHUB_TOKEN && (
                <div className="pt-2 border-t border-zinc-800/80">
                  <button
                    type="button"
                    onClick={() => {
                      setGhToken(DEFAULT_GITHUB_TOKEN);
                      handleConnectGitHub(DEFAULT_GITHUB_TOKEN);
                    }}
                    className="w-full p-2.5 rounded-xl bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 text-left transition font-mono text-xs flex items-center justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-emerald-400" />
                      <span>Quick Connect saved token (<strong>@{DEFAULT_GITHUB_OWNER}</strong>)</span>
                    </span>
                    <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                      1-Click Connect
                    </span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: VERCEL */}
          {activeTab === 'vercel' && (
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white font-mono flex items-center gap-2">
                    <Globe className="w-4 h-4 text-cyan-400" />
                    <span>Vercel Cloud Hosting</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Connect Vercel to automatically trigger continuous deployments when applications are created.
                  </p>
                </div>
                {integrations.vercel.connected ? (
                  <span className="px-2.5 py-1 bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-[11px] font-mono rounded-full flex items-center gap-1.5 shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Connected</span>
                  </span>
                ) : (
                  <span className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 text-zinc-400 text-[11px] font-mono rounded-full shrink-0">
                    Optional
                  </span>
                )}
              </div>

              {integrations.vercel.connected && integrations.vercel.user && (
                <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-white font-mono">
                      <span>{integrations.vercel.user.name || integrations.vercel.user.username}</span>
                    </div>
                    <div className="text-xs text-zinc-400 font-mono mt-0.5">
                      Vercel User: @{integrations.vercel.user.username}
                    </div>
                  </div>
                  <button
                    onClick={handleDisconnectVercel}
                    className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition"
                  >
                    Disconnect
                  </button>
                </div>
              )}

              {vError && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2 font-mono">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{vError}</span>
                </div>
              )}
              {vSuccess && (
                <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{vSuccess}</span>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-300 font-mono flex items-center justify-between">
                  <span>Vercel API Access Token</span>
                  <a
                    href="https://vercel.com/account/tokens"
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center gap-1"
                  >
                    <span>Generate token</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder="Enter Vercel access token..."
                    value={vToken}
                    onChange={(e) => setVToken(e.target.value)}
                    className="flex-1 px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 font-mono placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    onClick={handleConnectVercel}
                    disabled={vLoading}
                    className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 transition shrink-0"
                  >
                    {vLoading ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying...</span>
                      </>
                    ) : (
                      <>
                        <span>Connect</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: NEON DATABASE */}
          {activeTab === 'database' && (
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white font-mono flex items-center gap-2">
                    <Database className="w-4 h-4 text-violet-400" />
                    <span>Neon Serverless PostgreSQL</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Managed cloud database instance automatically connected to all provisioned applications.
                  </p>
                </div>
                <span className="px-2.5 py-1 bg-emerald-950/80 border border-emerald-800 text-emerald-400 text-[11px] font-mono rounded-full flex items-center gap-1.5 shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Active & Ready</span>
                </span>
              </div>

              <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 font-mono text-xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Host:</span>
                  <span className="text-zinc-200">ep-wild-cherry-aw3a6o5s.c-12.us-east-1.aws.neon.tech</span>
                </div>
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Region:</span>
                  <span className="text-zinc-200">AWS us-east-1 (N. Virginia)</span>
                </div>
                <div className="flex items-center justify-between text-zinc-400">
                  <span>Security:</span>
                  <span className="text-emerald-400">SSL require / Channel Binding</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-zinc-800/80 bg-zinc-900/40 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition"
          >
            Cancel
          </button>
          <button
            onClick={handleDone}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-mono font-medium flex items-center gap-2 transition shadow-lg shadow-emerald-950/40"
          >
            <span>Save & Continue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
