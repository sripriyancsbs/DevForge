import React, { useState } from 'react';
import {
  Search,
  Bell,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Layers,
  Menu,
  Plus
} from 'lucide-react';
import { OverviewData } from '../../types';

interface TopNavProps {
  onOpenCommandPalette: () => void;
  onToggleSidebar: () => void;
  onNavigateToCreate: () => void;
  overviewData?: OverviewData | null;
}

export const TopNav: React.FC<TopNavProps> = ({
  onOpenCommandPalette,
  onToggleSidebar,
  onNavigateToCreate,
  overviewData
}) => {
  const [showNotifications, setShowNotifications] = useState(false);

  // Compute realistic alerts from live service health & recent activity
  const failingServices = (overviewData?.service_health || []).filter(
    (s) => s.status === 'failed' || s.status === 'warning'
  );
  const failedDeployments = (overviewData?.recent_deployments || []).filter(
    (d) => d.status === 'failed'
  );

  const alertCount = failingServices.length + failedDeployments.length;

  return (
    <header className="h-14 border-b border-[#27272a] bg-[#0c0c0e] px-4 flex items-center justify-between sticky top-0 z-30">
      {/* Left section: Mobile menu button + Workspace Indicator */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden text-zinc-400 hover:text-zinc-100 p-1.5 rounded hover:bg-zinc-800"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Current Workspace Badge (Clean, truthful single-tenant indicator) */}
        <div className="flex items-center gap-2 text-xs font-medium text-zinc-300 px-2.5 py-1.5 rounded border border-zinc-800 bg-[#141417]">
          <Layers className="w-3.5 h-3.5 text-emerald-500" />
          <span className="font-mono">default-workspace</span>
          <span className="text-[10px] text-zinc-500 font-mono border-l border-zinc-800 pl-2 hidden sm:inline">
            Phase 1 Standalone
          </span>
        </div>
      </div>

      {/* Middle section: Global Search Bar */}
      <div className="flex-1 max-w-md mx-4 hidden sm:block">
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center justify-between px-3 py-1.5 rounded border border-zinc-800 bg-[#121215] text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 text-xs transition"
        >
          <div className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-zinc-500" />
            <span>Search applications, deployments, envs...</span>
          </div>
          <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-zinc-500 bg-zinc-800/80 rounded border border-zinc-700/60">
            <span>Ctrl</span><span>K</span>
          </kbd>
        </button>
      </div>

      {/* Right section: Action CTA, Notifications, Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={onNavigateToCreate}
          className="hidden md:flex items-center gap-1.5 bg-zinc-100 hover:bg-white text-zinc-950 px-2.5 py-1.5 rounded text-xs font-medium transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New App</span>
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-1.5 text-zinc-400 hover:text-zinc-100 rounded border border-zinc-800 hover:border-zinc-700 bg-[#121215] transition"
            aria-label="Platform Notifications"
          >
            <Bell className="w-4 h-4" />
            {alertCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-[#0c0c0e]" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 rounded-md border border-zinc-800 bg-[#121215] shadow-2xl z-50 overflow-hidden">
              <div className="p-3 border-b border-zinc-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-200">System Alerts</span>
                <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                  {alertCount} active
                </span>
              </div>
              <div className="divide-y divide-zinc-800/60 max-h-72 overflow-y-auto">
                {alertCount === 0 ? (
                  <div className="p-4 text-center text-xs text-zinc-500 font-mono flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>All services and deployments healthy</span>
                  </div>
                ) : (
                  <>
                    {failingServices.map((svc) => (
                      <div key={svc.id} className="p-3 hover:bg-zinc-800/30 transition text-xs">
                        <div className="flex items-start gap-2">
                          {svc.status === 'failed' ? (
                            <XCircle className="w-3.5 h-3.5 text-rose-500 mt-0.5 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-zinc-200 truncate">{svc.service_name}</div>
                            <div className="text-zinc-400 text-[11px] mt-0.5">
                              Status: {svc.status} • CPU: {svc.cpu_percent}% • Errors: {svc.error_rate}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                    {failedDeployments.map((dep) => (
                      <div key={dep.id} className="p-3 hover:bg-zinc-800/30 transition text-xs">
                        <div className="flex items-start gap-2">
                          <XCircle className="w-3.5 h-3.5 text-rose-500 mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-zinc-200 truncate">
                              Deployment failed: {dep.application_name} ({dep.version})
                            </div>
                            <div className="text-zinc-400 text-[11px] mt-0.5">{dep.commit_message}</div>
                            <div className="text-[10px] text-zinc-500 mt-1 font-mono">
                              Env: {dep.environment}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
              <div className="p-2 border-t border-zinc-800 bg-zinc-900/50 text-center">
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-[11px] text-zinc-400 hover:text-zinc-200"
                >
                  Close panel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User profile avatar - Truthful operator indicator */}
        <div className="flex items-center gap-2 pl-2 border-l border-zinc-800">
          <div className="w-7 h-7 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-300 font-semibold">
            DF
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-medium text-zinc-200 leading-tight">platform-admin</div>
            <div className="text-[10px] text-zinc-500 font-mono">Local Console</div>
          </div>
        </div>
      </div>
    </header>
  );
};
