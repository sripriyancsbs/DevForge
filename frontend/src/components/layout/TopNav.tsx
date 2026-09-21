import React, { useState, useEffect, useRef } from 'react';
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
  ChevronDown
} from 'lucide-react';
import { OverviewData, RemediationEvent, User } from '../../types';
import { api, getStoredUser, setStoredUser } from '../../services/api';

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

  const notificationRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Refresh authoritative current user info from backend
    api.getCurrentUser()
      .then((u) => {
        setCurrentUser(u);
        setStoredUser(u);
      })
      .catch(() => {});

    api.getApplications()
      .then((apps) => setApplicationsList(apps.map((a) => ({ id: a.id, name: a.name }))))
      .catch(() => setApplicationsList([]));

    api.listRemediationEvents()
      .then(setRemediationEvents)
      .catch(() => setRemediationEvents([]));
  }, []);

  // Outside click & Escape listeners for popovers
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (showNotifications && notificationRef.current && !notificationRef.current.contains(target)) {
        setShowNotifications(false);
      }
      if (showUserMenu && userMenuRef.current && !userMenuRef.current.contains(target)) {
        setShowUserMenu(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowNotifications(false);
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showNotifications, showUserMenu]);

  const toggleNotifications = () => {
    if (!showNotifications) {
      setShowUserMenu(false);
      setShowNotifications(true);
    } else {
      setShowNotifications(false);
    }
  };

  const toggleUserMenu = () => {
    if (!showUserMenu) {
      setShowNotifications(false);
      setShowUserMenu(true);
    } else {
      setShowUserMenu(false);
    }
  };

  const handleWorkspaceChange = async (wsId: number) => {
    try {
      const updated = await api.switchWorkspace(wsId);
      setCurrentUser(updated);
      setShowUserMenu(false);
      window.location.reload();
    } catch (err) {
      console.error('Failed to switch workspace:', err);
    }
  };

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

  const activeWorkspaceName = currentUser.active_workspace?.slug || 'default-workspace';

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

        {/* Current Workspace Badge */}
        <div id="top-nav-workspace-badge" className="flex items-center gap-2 text-xs font-medium text-zinc-300 px-2.5 py-1.5 rounded border border-zinc-800 bg-[#141417] min-w-0">
          <Layers className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span className="font-mono truncate max-w-[140px] sm:max-w-none">{activeWorkspaceName}</span>
        </div>
      </div>

      {/* Middle section: Search Bar */}
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

        {/* Actionable Notifications Popover */}
        <div className="relative" ref={notificationRef}>
          <button
            id="top-nav-bell-btn"
            data-testid="top-nav-bell-btn"
            onClick={toggleNotifications}
            className="relative p-1.5 text-zinc-400 hover:text-zinc-100 rounded border border-zinc-800 hover:border-zinc-700 bg-[#121215] transition cursor-pointer"
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

        {/* User profile avatar & Production User Menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            id="user-profile-menu-button"
            data-testid="user-profile-menu-button"
            onClick={toggleUserMenu}
            className="flex items-center gap-2 pl-2 border-l border-zinc-800 hover:opacity-90 transition cursor-pointer text-left focus:outline-none"
            aria-label="User session and account options"
          >
            <div className="w-7 h-7 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-300 font-semibold uppercase">
              {(currentUser.display_name || currentUser.username).slice(0, 2)}
            </div>
            <div className="hidden lg:block text-left">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-zinc-200 leading-tight">
                  {currentUser.display_name || currentUser.username}
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
                <span>{activeWorkspaceName}</span>
                <ChevronDown className="w-2.5 h-2.5" />
              </div>
            </div>
          </button>

          {showUserMenu && (
            <div
              id="user-profile-dropdown"
              data-testid="user-profile-dropdown"
              className="absolute right-0 mt-2 w-72 rounded-md border border-zinc-800 bg-[#141417] shadow-xl z-50 text-xs py-1 divide-y divide-zinc-800"
            >
              <div className="p-3">
                <div id="user-profile-name" className="text-xs font-semibold text-white">
                  {currentUser.display_name || currentUser.username}
                </div>
                <div id="user-profile-email" className="text-[11px] text-zinc-400 font-mono mt-0.5">
                  {currentUser.email}
                </div>
                
                {/* Authoritative Workspace & Role Details */}
                <div className="mt-2.5 p-2.5 rounded border border-zinc-800/80 bg-zinc-900/50 space-y-1.5">
                  <div id="user-profile-workspace" className="text-xs text-zinc-300 font-mono">
                    <span className="text-zinc-500">Workspace: </span>
                    <span className="text-zinc-200 font-medium">{activeWorkspaceName}</span>
                  </div>
                  <div id="user-profile-role" className="text-xs text-zinc-300 font-mono flex items-center justify-between">
                    <span>
                      <span className="text-zinc-500">Role: </span>
                      <span className={`font-mono font-bold uppercase ${
                        currentUser.role === 'ADMIN'
                          ? 'text-violet-400'
                          : currentUser.role === 'OPERATOR'
                          ? 'text-emerald-400'
                          : currentUser.role === 'DEVELOPER'
                          ? 'text-amber-400'
                          : 'text-zinc-400'
                      }`}>
                        {currentUser.role}
                      </span>
                    </span>
                    <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">
                      Authoritative
                    </span>
                  </div>
                </div>

                {/* Workspace Switching (Only visible if user belongs to multiple workspaces) */}
                {currentUser.workspaces && currentUser.workspaces.length > 1 && (
                  <div className="mt-2.5 pt-2 border-t border-zinc-800/60">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-1.5">
                      Switch Workspace
                    </div>
                    <div className="space-y-1">
                      {currentUser.workspaces.map((ws) => (
                        <button
                          key={ws.id}
                          id={`switch-workspace-${ws.slug}`}
                          onClick={() => handleWorkspaceChange(ws.id)}
                          className={`w-full text-left px-2 py-1.5 rounded text-xs flex items-center justify-between font-mono transition cursor-pointer ${
                            (currentUser.active_workspace?.id === ws.id || activeWorkspaceName === ws.slug)
                              ? 'bg-zinc-800 text-emerald-400 border border-zinc-700'
                              : 'text-zinc-300 hover:bg-zinc-800/50'
                          }`}
                        >
                          <span className="truncate">{ws.name}</span>
                          <span className="text-[10px] text-zinc-500 uppercase ml-2">{ws.role}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="p-2">
                <button
                  id="user-logout-button"
                  data-testid="user-logout-button"
                  onClick={async () => {
                    await api.logout();
                    const viewer: User = {
                      id: 4,
                      username: 'viewer',
                      email: 'viewer@devforge.internal',
                      display_name: 'Viewer',
                      role: 'VIEWER',
                      is_active: true,
                      status: 'active',
                      permissions: ['view:all'],
                      workspaces: [{ id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'VIEWER' }],
                      active_workspace: { id: 1, name: 'Default Workspace', slug: 'default-workspace', role: 'VIEWER' }
                    };
                    setStoredUser(viewer);
                    setCurrentUser(viewer);
                    setShowUserMenu(false);
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded text-rose-400 hover:bg-rose-950/30 hover:text-rose-300 transition text-[11px] cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
