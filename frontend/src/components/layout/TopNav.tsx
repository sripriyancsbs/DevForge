import React, { useState, useEffect } from 'react';
import {
  Search,
  Bell,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Layers,
  Menu,
  Plus,
  ArrowRight,
  Wrench,
  Shield,
  User as UserIcon,
  ChevronDown
} from 'lucide-react';
import { OverviewData, RemediationEvent, User, Role } from '../../types';
import { api, getStoredUser } from '../../services/api';

interface TopNavProps {
  onToggleSidebar: () => void;
  onNavigateToCreate: () => void;
  onNavigateToApp: (appName: string, tab?: string) => void;
  overviewData?: OverviewData | null;
}

const formatRelativeTime = (isoString?: string): string => {
  if (!isoString) return 'recently';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
};

export const TopNav: React.FC<TopNavProps> = ({
  onToggleSidebar,
  onNavigateToCreate,
  onNavigateToApp,
  overviewData
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [currentUser, setCurrentUser] = useState<User>(getStoredUser());
  const [searchQuery, setSearchQuery] = useState('');
  const [remediationEvents, setRemediationEvents] = useState<RemediationEvent[]>([]);
  const [applicationsList, setApplicationsList] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    api.getApplications()
      .then((apps) => setApplicationsList(apps.map((a) => ({ id: a.id, name: a.name }))))
      .catch(() => setApplicationsList([]));
    api.listRemediationEvents()
      .then(setRemediationEvents)
      .catch(() => setRemediationEvents([]));
  }, []);

  const resolveAppName = (appId: number): string => {
    const found = applicationsList.find((a) => a.id === appId);
    return found?.name || `app-${appId}`;
  };

  // Compute real alerts from live service health, recent deployments, and remediation incidents
  const failingServices = (overviewData?.service_health || []).filter(
    (s) => s.status === 'failed' || s.status === 'warning'
  );
  const failedDeployments = (overviewData?.recent_deployments || []).filter(
    (d) => d.status === 'failed' || d.status === 'rolled_back'
  );
  const activeRemediations = remediationEvents.filter(
    (r) => ['DETECTED', 'EVALUATING', 'REMEDIATING', 'VERIFYING', 'ESCALATED'].includes(r.status)
  );

  const alertCount = failingServices.length + failedDeployments.length + activeRemediations.length;

  const handleNotificationClick = (appName: string, tab: string) => {
    setShowNotifications(false);
    onNavigateToApp(appName, tab);
  };

  return (
    <header className="h-14 border-b border-[#27272a] bg-[#0c0c0e] px-4 flex items-center justify-between sticky top-0 z-30 min-w-0 w-full">
      {/* Left section: Mobile menu button + Workspace Indicator */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          onClick={onToggleSidebar}
          className="md:hidden text-zinc-400 hover:text-zinc-100 p-1.5 rounded hover:bg-zinc-800 shrink-0"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Current Workspace Badge - Truthful, No Platform Version Badge */}
        <div className="flex items-center gap-2 text-xs font-medium text-zinc-300 px-2.5 py-1.5 rounded border border-zinc-800 bg-[#141417] min-w-0">
          <Layers className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span className="font-mono truncate max-w-[120px] sm:max-w-none">default-workspace</span>
        </div>
      </div>

      {/* Middle section: Clean Search Bar without Ctrl+K prompt */}
      <div className="flex-1 max-w-md mx-4 hidden sm:block">
        <div className="relative w-full">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search applications, services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && searchQuery.trim()) {
                onNavigateToApp(searchQuery.trim(), 'overview');
              }
            }}
            className="w-full pl-9 pr-3 py-1.5 rounded border border-zinc-800 bg-[#121215] text-zinc-200 placeholder-zinc-500 text-xs font-mono focus:outline-none focus:border-zinc-600 transition"
          />
        </div>
      </div>

      {/* Right section: Action CTA, Notifications, Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={onNavigateToCreate}
          className="hidden md:flex items-center gap-1.5 bg-zinc-100 hover:bg-white text-zinc-950 px-2.5 py-1.5 rounded text-xs font-medium transition shadow-xs"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New App</span>
        </button>

        {/* Actionable Notifications */}
        <div className="relative">
          <button
            id="top-nav-bell-btn"
            data-testid="top-nav-bell-btn"
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
            <div id="notifications-panel" data-testid="notifications-panel" className="fixed sm:absolute left-4 sm:left-auto right-4 sm:right-0 top-14 sm:top-full mt-2 sm:w-96 rounded-md border border-zinc-800 bg-[#121215] shadow-2xl z-50 overflow-hidden">
              <div className="p-3 border-b border-zinc-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-200">System Notifications</span>
                <span className="text-[10px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                  {alertCount} active
                </span>
              </div>

              <div className="divide-y divide-zinc-800/60 max-h-80 overflow-y-auto">
                {alertCount === 0 ? (
                  <div className="p-4 text-center text-xs text-zinc-500 font-mono flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>All services and deployments healthy</span>
                  </div>
                ) : (
                  <>
                    {/* Phase 11: Self-Healing & Remediation Notifications */}
                    {remediationEvents.map((rem) => {
                      const appName = resolveAppName(rem.application_id);
                      let title = 'Application Unhealthy';
                      let desc = rem.details || 'Health check failed continuously.';
                      let badgeColor = 'text-amber-400';
                      let icon = <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />;

                      if (rem.status === 'RECOVERED') {
                        title = 'Application Recovered';
                        desc = 'Health restored after automated remediation.';
                        badgeColor = 'text-emerald-400';
                        icon = <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />;
                      } else if (rem.status === 'ESCALATED' || rem.status === 'FAILED') {
                        title = 'Automatic Remediation Failed';
                        desc = `Application remains unhealthy after ${rem.attempts || 3} attempts. Manual investigation required.`;
                        badgeColor = 'text-rose-400';
                        icon = <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />;
                      } else if (rem.status === 'REMEDIATING' || rem.status === 'VERIFYING') {
                        title = 'Remediation In Progress';
                        desc = `Automated remediation initiated for ${rem.event_type}.`;
                        badgeColor = 'text-blue-400';
                        icon = <Wrench className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />;
                      }

                      return (
                        <div
                          key={`rem-${rem.id}`}
                          id={`notification-rem-${rem.id}`}
                          data-testid="notification-item"
                          onClick={() => handleNotificationClick(appName, 'monitoring')}
                          className="p-3 hover:bg-zinc-800/40 cursor-pointer transition text-xs group border-l-2 border-transparent hover:border-emerald-500"
                          role="button"
                          tabIndex={0}
                        >
                          <div className="flex items-start gap-2.5">
                            {icon}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-1">
                                <span className={`font-semibold ${badgeColor}`}>{title}</span>
                                <span className="text-[10px] text-zinc-500 font-mono">
                                  {formatRelativeTime(rem.created_at)}
                                </span>
                              </div>

                              <div className="font-mono text-zinc-200 text-xs mt-0.5">
                                {appName}
                                <span className="text-zinc-500 ml-1.5 capitalize font-sans">({rem.environment_id})</span>
                                <span className="text-zinc-500 ml-1 font-mono text-[11px]">• Event #{rem.id}</span>
                              </div>

                              <div className="text-zinc-400 text-[11px] mt-1 bg-zinc-950/60 p-1.5 rounded border border-zinc-800/50">
                                {desc}
                              </div>

                              <div className="mt-1.5 flex items-center text-[10px] text-emerald-400 font-mono group-hover:text-emerald-300">
                                <span>Inspect remediation in Monitoring tab</span>
                                <ArrowRight className="w-3 h-3 ml-1 group-hover:translate-x-0.5 transition-transform" />
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {/* Failed or Rolled Back Deployments */}
                    {failedDeployments.map((dep) => (
                      <div
                        key={`dep-${dep.id}`}
                        id={`notification-dep-${dep.id}`}
                        data-testid="notification-item"
                        onClick={() => handleNotificationClick(dep.application_name, 'deployments')}
                        className="p-3 hover:bg-zinc-800/40 cursor-pointer transition text-xs group"
                        role="button"
                        tabIndex={0}
                      >
                        <div className="flex items-start gap-2.5">
                          <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-semibold text-rose-400">
                                {dep.status === 'rolled_back' ? 'Deployment Rolled Back' : 'Deployment Failed'}
                              </span>
                              <span className="text-[10px] text-zinc-500 font-mono">
                                {formatRelativeTime(dep.created_at)}
                              </span>
                            </div>

                            <div className="font-mono text-zinc-200 text-xs mt-0.5">
                              {dep.application_name}
                              <span className="text-zinc-500 ml-1.5 capitalize font-sans">({dep.environment})</span>
                              <span className="text-zinc-500 ml-1 font-mono text-[11px]">• #{dep.id}</span>
                            </div>

                            <div className="text-zinc-400 text-[11px] mt-1 bg-zinc-950/60 p-1.5 rounded border border-zinc-800/50">
                              <span className="text-zinc-500 font-mono">Reason: </span>
                              {dep.commit_message || 'Container failed health check or timeout'}
                            </div>

                            <div className="mt-1.5 flex items-center text-[10px] text-emerald-400 font-mono group-hover:text-emerald-300">
                              <span>View deployment details</span>
                              <ArrowRight className="w-3 h-3 ml-1 group-hover:translate-x-0.5 transition-transform" />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Failing or Warning Services */}
                    {failingServices.map((svc) => (
                      <div
                        key={`svc-${svc.id}`}
                        id={`notification-svc-${svc.id}`}
                        data-testid="notification-item"
                        onClick={() => handleNotificationClick(svc.service_name, 'monitoring')}
                        className="p-3 hover:bg-zinc-800/40 cursor-pointer transition text-xs group"
                        role="button"
                        tabIndex={0}
                      >
                        <div className="flex items-start gap-2.5">
                          {svc.status === 'failed' ? (
                            <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <span className={`font-semibold ${svc.status === 'failed' ? 'text-rose-400' : 'text-amber-400'}`}>
                                {svc.status === 'failed' ? 'Service Down' : 'High Latency / Degraded'}
                              </span>
                              <span className="text-[10px] text-zinc-500 font-mono">
                                {formatRelativeTime(svc.updated_at)}
                              </span>
                            </div>

                            <div className="font-mono text-zinc-200 text-xs mt-0.5">
                              {svc.service_name}
                            </div>

                            <div className="text-zinc-400 text-[11px] mt-1 bg-zinc-950/60 p-1.5 rounded border border-zinc-800/50">
                              <span className="text-zinc-500 font-mono">Telemetry: </span>
                              CPU: {svc.cpu_percent}% • Errors: {svc.error_rate} • Uptime: {svc.uptime}
                            </div>

                            <div className="mt-1.5 flex items-center text-[10px] text-emerald-400 font-mono group-hover:text-emerald-300">
                              <span>View application monitoring</span>
                              <ArrowRight className="w-3 h-3 ml-1 group-hover:translate-x-0.5 transition-transform" />
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
                  Close notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User profile avatar & RBAC Role Switcher */}
        <div className="relative">
          <button
            id="user-profile-menu-button"
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 pl-2 border-l border-zinc-800 hover:opacity-90 transition cursor-pointer text-left focus:outline-none"
            aria-label="User session and role options"
          >
            <div className="w-7 h-7 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-300 font-semibold uppercase">
              {currentUser.username.slice(0, 2)}
            </div>
            <div className="hidden lg:block text-left">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-zinc-200 leading-tight">
                  {currentUser.username}
                </span>
                <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase font-semibold ${
                  currentUser.role === 'ADMIN'
                    ? 'text-violet-400 bg-violet-950/60 border-violet-800/60'
                    : currentUser.role === 'OPERATOR'
                    ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60'
                    : currentUser.role === 'DEVELOPER'
                    ? 'text-amber-400 bg-amber-950/60 border-amber-800/60'
                    : 'text-zinc-400 bg-zinc-800 border-zinc-700'
                }`}>
                  {currentUser.role}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500 font-mono flex items-center gap-1">
                <span>RBAC Session</span>
                <ChevronDown className="w-2.5 h-2.5" />
              </div>
            </div>
          </button>

          {showUserMenu && (
            <div
              id="user-profile-dropdown"
              className="absolute right-0 mt-2 w-64 rounded-md border border-zinc-800 bg-[#141417] shadow-xl z-50 text-xs py-1 divide-y divide-zinc-800"
            >
              <div className="p-3">
                <div className="text-xs font-semibold text-white">{currentUser.username}</div>
                <div className="text-[11px] text-zinc-400 font-mono mt-0.5">{currentUser.email}</div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[11px] text-zinc-400">Active Role:</span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${
                    currentUser.role === 'ADMIN'
                      ? 'text-violet-400 bg-violet-950/60 border-violet-800/60'
                      : currentUser.role === 'OPERATOR'
                      ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60'
                      : currentUser.role === 'DEVELOPER'
                      ? 'text-amber-400 bg-amber-950/60 border-amber-800/60'
                      : 'text-zinc-400 bg-zinc-800 border-zinc-700'
                  }`}>
                    {currentUser.role}
                  </span>
                </div>
              </div>

              <div className="p-2 space-y-1">
                <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 px-2 py-1">
                  Switch Active Role (RBAC)
                </div>
                {(['ADMIN', 'OPERATOR', 'DEVELOPER', 'VIEWER'] as Role[]).map((r) => (
                  <button
                    key={r}
                    id={`switch-role-${r.toLowerCase()}`}
                    onClick={() => {
                      const updated = api.switchRoleSession(r);
                      setCurrentUser(updated);
                      setShowUserMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded flex items-center justify-between transition ${
                      currentUser.role === r
                        ? 'bg-zinc-800/80 text-white font-medium'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                    }`}
                  >
                    <span>{r}</span>
                    {currentUser.role === r && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    )}
                  </button>
                ))}
              </div>

              <div className="p-2">
                <button
                  id="user-logout-button"
                  onClick={() => {
                    api.logout();
                    const viewer = api.switchRoleSession('VIEWER');
                    setCurrentUser(viewer);
                    setShowUserMenu(false);
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded text-rose-400 hover:bg-rose-950/30 hover:text-rose-300 transition text-[11px]"
                >
                  Clear Session / Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
