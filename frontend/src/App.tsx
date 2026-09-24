import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Sidebar, NavigationTab } from './components/layout/Sidebar';
import { TopNav } from './components/layout/TopNav';
import { OverviewPage } from './pages/OverviewPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { ApplicationDetailPage, AppDetailTab } from './pages/ApplicationDetailPage';
import { CreateApplicationPage } from './pages/CreateApplicationPage';
import { ActivityPage } from './pages/ActivityPage';
import { SettingsPage } from './pages/SettingsPage';
import { SignInPage } from './pages/SignInPage';
import { SignUpPage } from './pages/SignUpPage';
import { ConnectionsModal } from './components/ConnectionsModal';
import { hasCompletedConnectionsOnboarding } from './services/integrationsService';
import { api, getAuthToken, getStoredUser, setStoredUser, clearAuthToken } from './services/api';
import { Application, Deployment, Environment, OverviewData, User } from './types';
import { ArrowLeft, AlertCircle } from 'lucide-react';

interface RouteState {
  view: 'overview' | 'applications' | 'create-application' | 'application-detail' | 'activity' | 'settings' | 'signin' | 'signup';
  appIdentifier?: string;
  appTab?: AppDetailTab;
}

const parseRoute = (pathname: string): RouteState => {
  const clean = pathname.replace(/^\/+|\/+$/g, '');
  const segments = clean.split('/').filter(Boolean);

  if (segments.length > 0) {
    if (segments[0] === 'signin' || segments[0] === 'login') {
      return { view: 'signin' };
    }
    if (segments[0] === 'signup' || segments[0] === 'register') {
      return { view: 'signup' };
    }
  }

  if (segments.length === 0 || segments[0] === 'overview') {
    return { view: 'overview' };
  }

  if (segments[0] === 'activity') {
    return { view: 'activity' };
  }

  if (segments[0] === 'settings') {
    return { view: 'settings' };
  }

  if (segments[0] === 'create-application') {
    return { view: 'create-application' };
  }

  if (segments[0] === 'applications') {
    if (segments.length === 1) {
      return { view: 'applications' };
    }
    if (segments[1] === 'create') {
      return { view: 'create-application' };
    }
    const appIdentifier = segments[1];
    const validTabs: AppDetailTab[] = [
      'overview',
      'deployments',
      'environments',
      'infrastructure',
      'automation',
      'monitoring',
      'logs'
    ];
    const rawTab = segments[2] ? segments[2].toLowerCase() : 'overview';
    const appTab = validTabs.includes(rawTab as AppDetailTab) ? (rawTab as AppDetailTab) : 'overview';
    return {
      view: 'application-detail',
      appIdentifier,
      appTab
    };
  }

  // Redirect legacy top-level routes to applications catalog
  if (['deployments', 'environments', 'infrastructure', 'automation', 'monitoring', 'gitops'].includes(segments[0])) {
    return { view: 'applications' };
  }

  return { view: 'overview' };
};

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(() => getStoredUser());
  const [route, setRoute] = useState<RouteState>(() => {
    if (typeof window === 'undefined') return { view: 'signin' };
    const parsed = parseRoute(window.location.pathname);
    const token = getAuthToken();
    if (!token) {
      if (parsed.view === 'signup') return { view: 'signup' };
      return { view: 'signin' };
    }
    return parsed;
  });

  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  // Core platform data
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(false);

  // Dedicated detail page application state (loaded from cache or on demand)
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [appLoadingError, setAppLoadingError] = useState<string | null>(null);

  // Global Notification / Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showConnectionsModal, setShowConnectionsModal] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleLogout = useCallback(async () => {
    clearAuthToken();
    setCurrentUser(null);
    setOverviewData(null);
    setApplications([]);
    setEnvironments([]);
    setDeployments([]);
    setActiveApp(null);
    setAppLoadingError(null);
    if (typeof window !== 'undefined') {
      window.history.replaceState({ view: 'signin' }, '', '/signin');
    }
    setRoute({ view: 'signin' });
    try {
      await api.logout();
    } catch {
      // Ignore network errors on logout
    }
  }, []);

  // Push route to history
  const navigateToRoute = useCallback((newRoute: RouteState, updateHistory = true) => {
    setRoute(newRoute);
    if (updateHistory && typeof window !== 'undefined') {
      let targetPath = '/';
      if (newRoute.view === 'signin') targetPath = '/signin';
      else if (newRoute.view === 'signup') targetPath = '/signup';
      else if (newRoute.view === 'overview') targetPath = '/';
      else if (newRoute.view === 'applications') targetPath = '/applications';
      else if (newRoute.view === 'create-application') targetPath = '/applications/create';
      else if (newRoute.view === 'activity') targetPath = '/activity';
      else if (newRoute.view === 'settings') targetPath = '/settings';
      else if (newRoute.view === 'application-detail' && newRoute.appIdentifier) {
        targetPath = newRoute.appTab && newRoute.appTab !== 'overview'
          ? `/applications/${encodeURIComponent(newRoute.appIdentifier)}/${newRoute.appTab}`
          : `/applications/${encodeURIComponent(newRoute.appIdentifier)}`;
      }

      if (window.location.pathname !== targetPath) {
        window.history.pushState(newRoute, '', targetPath);
      }
    }
  }, []);

  // Check auth session on startup
  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setCurrentUser(null);
      if (route.view !== 'signup' && route.view !== 'signin') {
        window.history.replaceState({ view: 'signin' }, '', '/signin');
        setRoute({ view: 'signin' });
      }
      return;
    }

    api.getCurrentUser()
      .then((u) => {
        if (u) {
          setCurrentUser(u);
          setStoredUser(u);
        } else {
          handleLogout();
        }
      })
      .catch(() => {
        handleLogout();
      });
  }, [handleLogout]);

  // Protected route guard: redirect to /signin if unauthenticated
  useEffect(() => {
    if (!currentUser) {
      if (route.view !== 'signin' && route.view !== 'signup') {
        window.history.replaceState({ view: 'signin' }, '', '/signin');
        setRoute({ view: 'signin' });
      }
    }
  }, [currentUser, route.view]);

  // Listen to browser Back / Forward
  useEffect(() => {
    const handlePopState = () => {
      const parsed = parseRoute(window.location.pathname);
      const token = getAuthToken();
      if (!token) {
        if (parsed.view !== 'signin' && parsed.view !== 'signup') {
          window.history.replaceState({ view: 'signin' }, '', '/signin');
          setRoute({ view: 'signin' });
          return;
        }
      }
      setRoute(parsed);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Fetch initial platform data
  const loadPlatformData = useCallback(async () => {
    if (!getAuthToken()) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [ov, apps, envs, deps] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getApplications().catch(() => []),
        api.getEnvironments().catch(() => []),
        api.getDeployments().catch(() => [])
      ]);

      if (ov) setOverviewData(ov);
      if (apps) setApplications(apps);
      if (envs) setEnvironments(envs);
      if (deps) setDeployments(deps);
    } catch (err) {
      console.error('Failed to load platform data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      loadPlatformData();
    }
  }, [currentUser, loadPlatformData]);

  const handleAuthSuccess = (user: User) => {
    setCurrentUser(user);
    setStoredUser(user);
    loadPlatformData();
    navigateToRoute({ view: 'overview' });
    // After sign in, immediately prompt for connections (GitHub, Vercel, Neon DB)
    setShowConnectionsModal(true);
  };

  // Synchronize active application when route changes to application-detail
  useEffect(() => {
    if (!currentUser) return;
    if (route.view === 'application-detail' && route.appIdentifier) {
      const identifier = route.appIdentifier.trim().toLowerCase();

      if (
        activeApp &&
        (activeApp.name.toLowerCase() === identifier ||
          activeApp.slug.toLowerCase() === identifier ||
          String(activeApp.id) === identifier)
      ) {
        setAppLoadingError(null);
        return;
      }

      // Look in existing applications
      const found = applications.find(
        (a) => a.name.toLowerCase() === identifier || a.slug.toLowerCase() === identifier || String(a.id) === identifier
      );

      if (found) {
        setActiveApp(found);
        setAppLoadingError(null);
      } else if (!loading) {
        api.getApplicationDetails(route.appIdentifier)
          .then((res) => {
            setActiveApp(res.application);
            setAppLoadingError(null);
            setApplications((prev) => {
              const exists = prev.some(
                (a) => a.id === res.application.id || a.name.toLowerCase() === res.application.name.toLowerCase()
              );
              return exists ? prev : [res.application, ...prev];
            });
          })
          .catch((err) => {
            setActiveApp(null);
            const errMsg = err?.message?.toLowerCase() || '';
            if (errMsg.includes('forbidden') || errMsg.includes('403') || errMsg.includes('permission')) {
              setAppLoadingError(`Access Denied: You do not have permission to view application "${route.appIdentifier}".`);
            } else if (errMsg.includes('unauthorized') || errMsg.includes('401')) {
              setAppLoadingError(`Authentication required to view application "${route.appIdentifier}".`);
            } else {
              setAppLoadingError(`Application "${route.appIdentifier}" was not found.`);
            }
          });
      }
    } else {
      setActiveApp(null);
      setAppLoadingError(null);
    }
  }, [route.view, route.appIdentifier, applications, loading, activeApp, currentUser]);

  // Navigation handlers
  const handleSelectTab = (tab: NavigationTab) => {
    if (tab === 'overview') navigateToRoute({ view: 'overview' });
    else if (tab === 'applications') navigateToRoute({ view: 'applications' });
    else if (tab === 'create-application') navigateToRoute({ view: 'create-application' });
    else if (tab === 'activity') navigateToRoute({ view: 'activity' });
    else if (tab === 'settings') navigateToRoute({ view: 'settings' });
  };

  const handleSelectApplication = (appNameOrSlug: string, tab: AppDetailTab = 'overview') => {
    navigateToRoute({
      view: 'application-detail',
      appIdentifier: appNameOrSlug,
      appTab: tab
    });
  };

  const handleTriggerDeploy = async (appId: number, version: string, env: string) => {
    try {
      await api.triggerDeployment({
        application_id: appId,
        version,
        environment: env,
        commit_message: `Rollout initiated from console (${version})`
      });
      showToast(`Deployment initiated for revision ${version} on ${env}`);
      await loadPlatformData();
      if (activeApp && activeApp.id === appId) {
        setActiveApp({
          ...activeApp,
          version,
          last_deployment_at: new Date().toISOString()
        });
      }
    } catch (err: any) {
      showToast(`Deployment failed: ${err.message}`);
      throw err;
    }
  };

  const handleCreateApplication = async (data: any): Promise<any> => {
    const res = await api.createApplication(data);
    showToast(`Application '${res.application.name}' created and queued for provisioning`);
    setActiveApp(res.application);
    setAppLoadingError(null);
    setApplications((prev) => {
      const exists = prev.some(
        (a) => a.id === res.application.id || a.name.toLowerCase() === res.application.name.toLowerCase()
      );
      return exists ? prev : [res.application, ...prev];
    });
    handleSelectApplication(res.application.name, 'overview');
    loadPlatformData();
    return res;
  };

  // Derive sidebar current tab
  const sidebarTab: NavigationTab = useMemo(() => {
    if (route.view === 'overview') return 'overview';
    if (route.view === 'activity') return 'activity';
    if (route.view === 'settings') return 'settings';
    return 'applications';
  }, [route.view]);

  // If unauthenticated, render public authentication view
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex flex-col w-full">
        <TopNav
          currentUser={null}
          onLogout={handleLogout}
          onNavigateToSignIn={() => navigateToRoute({ view: 'signin' })}
          onNavigateToSignUp={() => navigateToRoute({ view: 'signup' })}
          onNavigateToApp={() => {}}
        />
        <main className="flex-1 flex items-center justify-center p-4">
          {route.view === 'signup' ? (
            <SignUpPage
              onSuccess={handleAuthSuccess}
              onNavigateToSignIn={() => navigateToRoute({ view: 'signin' })}
            />
          ) : (
            <SignInPage
              onSuccess={handleAuthSuccess}
              onNavigateToSignUp={() => navigateToRoute({ view: 'signup' })}
            />
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex w-full">
      {/* Primary Sidebar (Requirement 1: Overview, Applications, Activity, Settings) */}
      <Sidebar
        currentTab={sidebarTab}
        onSelectTab={handleSelectTab}
        isOpenMobile={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
        applicationsCount={applications.length}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0 w-full md:w-[calc(100%-15rem)]">
        {/* Top Navigation Bar */}
        <TopNav
          onToggleSidebar={() => setIsMobileNavOpen(!isMobileNavOpen)}
          onNavigateToCreate={() => navigateToRoute({ view: 'create-application' })}
          onNavigateToApp={(appName, tab) => handleSelectApplication(appName, (tab as AppDetailTab) || 'overview')}
          overviewData={overviewData}
          currentUser={currentUser}
          onLogout={handleLogout}
          onNavigateToSignIn={() => navigateToRoute({ view: 'signin' })}
          onNavigateToSignUp={() => navigateToRoute({ view: 'signup' })}
          onOpenConnections={() => setShowConnectionsModal(true)}
        />

        {/* Global Action Toast Banner */}
        {toastMessage && (
          <div className="bg-emerald-950/80 border-b border-emerald-800/60 px-4 py-2 text-xs font-mono text-emerald-300 flex items-center justify-between animate-in fade-in duration-150">
            <span>✓ {toastMessage}</span>
            <button onClick={() => setToastMessage(null)} className="text-emerald-400 hover:text-white">
              ✕
            </button>
          </div>
        )}

        {/* Views */}
        <main className="flex-1 pb-16 min-w-0 w-full">
          {/* 1. Global Overview */}
          {route.view === 'overview' && (
            <OverviewPage
              data={overviewData}
              loading={loading}
              onRefresh={loadPlatformData}
              onSelectApplication={(appName) => handleSelectApplication(appName, 'overview')}
              onNavigateTab={handleSelectTab}
            />
          )}

          {/* 2. Applications Catalog / Inventory */}
          {route.view === 'applications' && (
            <ApplicationsPage
              applications={applications}
              loading={loading}
              onSelectApplication={(appName) => handleSelectApplication(appName, 'overview')}
              onNavigateToCreate={() => navigateToRoute({ view: 'create-application' })}
              onTriggerDeploy={handleTriggerDeploy}
            />
          )}

          {/* 3. Create Application Flow */}
          {route.view === 'create-application' && (
            <CreateApplicationPage
              onBack={() => navigateToRoute({ view: 'applications' })}
              onSuccess={(app) => {
                handleSelectApplication(app.name, 'overview');
              }}
              onCreateApp={handleCreateApplication}
            />
          )}

          {/* 4. Dedicated Application Detail Page */}
          {route.view === 'application-detail' && (
            <>
              {activeApp ? (
                <ApplicationDetailPage
                  app={activeApp}
                  initialTab={route.appTab || 'overview'}
                  onTabChange={(tab) => {
                    if (activeApp) {
                      navigateToRoute({
                        view: 'application-detail',
                        appIdentifier: activeApp.name,
                        appTab: tab
                      });
                    }
                  }}
                  onBack={() => navigateToRoute({ view: 'applications' })}
                  onTriggerDeploy={handleTriggerDeploy}
                  allDeployments={deployments}
                  allHealth={overviewData?.service_health || []}
                  onRefreshData={loadPlatformData}
                />
              ) : appLoadingError ? (
                <div className="p-8 max-w-xl mx-auto mt-12 text-center space-y-4 font-mono">
                  <div className="w-12 h-12 rounded-full bg-rose-950/60 border border-rose-800/60 text-rose-400 flex items-center justify-center mx-auto">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                  <h2 className="text-base font-bold text-white">Application Not Found</h2>
                  <p className="text-xs text-zinc-400 font-sans">
                    {appLoadingError}
                  </p>
                  <button
                    onClick={() => navigateToRoute({ view: 'applications' })}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs transition"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Return to Applications</span>
                  </button>
                </div>
              ) : (
                <div className="p-8 flex items-center justify-center text-zinc-500 font-mono text-xs">
                  Loading application details...
                </div>
              )}
            </>
          )}

          {/* 5. Global Platform Activity */}
          {route.view === 'activity' && (
            <ActivityPage
              onSelectApplication={(appName) => handleSelectApplication(appName, 'overview')}
            />
          )}

          {/* 6. Settings */}
          {route.view === 'settings' && <SettingsPage />}
        </main>
        {/* Modal for Platform Integrations */}
        <ConnectionsModal
          isOpen={showConnectionsModal}
          onClose={() => setShowConnectionsModal(false)}
        />
      </div>
    </div>
  );
};
