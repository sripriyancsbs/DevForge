import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar, NavigationTab } from './components/layout/Sidebar';
import { TopNav } from './components/layout/TopNav';
import { CommandPalette } from './components/common/CommandPalette';
import { AppDetailDrawer } from './components/modules/AppDetailDrawer';
import { OverviewPage } from './pages/OverviewPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { CreateApplicationPage } from './pages/CreateApplicationPage';
import { EnvironmentsPage } from './pages/EnvironmentsPage';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { InfrastructurePage } from './pages/InfrastructurePage';
import { MonitoringPage } from './pages/MonitoringPage';
import { ActivityPage } from './pages/ActivityPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './services/api';
import { Application, Deployment, Environment, OverviewData } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('overview');
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Core platform data
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);

  // Slide-over detail state
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  // Notification / Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Fetch all initial platform data
  const loadPlatformData = useCallback(async () => {
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
    loadPlatformData();
  }, [loadPlatformData]);

  // Handle row click to open Application details
  const handleSelectApplication = (appNameOrSlug: string) => {
    const found = applications.find(
      (a) => a.name === appNameOrSlug || a.slug === appNameOrSlug
    );
    if (found) {
      setSelectedApp(found);
    } else {
      // If navigating from Overview recent deployments before applications are mapped
      api.getApplicationDetails(appNameOrSlug)
        .then((res) => setSelectedApp(res.application))
        .catch(console.error);
    }
  };

  // Handle triggering a deployment
  const handleTriggerDeploy = async (appId: number, version: string, env: string) => {
    try {
      const newDep = await api.triggerDeployment({
        application_id: appId,
        version,
        environment: env,
        commit_message: `Manual rollout triggered from console (${version})`
      });
      showToast(`Deployment initiated for revision ${version}`);
      await loadPlatformData();
      // update selectedApp version if open
      if (selectedApp && selectedApp.id === appId) {
        setSelectedApp({ ...selectedApp, version, last_deployment_at: new Date().toISOString() });
      }
    } catch (err: any) {
      showToast(`Deployment failed: ${err.message}`);
    }
  };

  // Handle creating an application
  const handleCreateApplication = async (data: any): Promise<any> => {
    const res = await api.createApplication(data);
    showToast(`Application '${res.application.name}' provisioned successfully`);
    await loadPlatformData();
    return res;
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        isOpenMobile={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onToggleSidebar={() => setIsMobileNavOpen(!isMobileNavOpen)}
          onNavigateToCreate={() => setCurrentTab('create-application')}
          overviewData={overviewData}
        />

        {/* Global Toast Banner */}
        {toastMessage && (
          <div className="bg-emerald-950/80 border-b border-emerald-800/60 px-4 py-2 text-xs font-mono text-emerald-300 flex items-center justify-between animate-in fade-in duration-150">
            <span>✓ {toastMessage}</span>
            <button onClick={() => setToastMessage(null)} className="text-emerald-400 hover:text-white">
              ✕
            </button>
          </div>
        )}

        <main className="flex-1 pb-16">
          {currentTab === 'overview' && (
            <OverviewPage
              data={overviewData}
              loading={loading}
              onRefresh={loadPlatformData}
              onSelectApplication={handleSelectApplication}
              onNavigateTab={setCurrentTab}
            />
          )}

          {currentTab === 'applications' && (
            <ApplicationsPage
              applications={applications}
              loading={loading}
              onSelectApplication={handleSelectApplication}
              onNavigateToCreate={() => setCurrentTab('create-application')}
              onTriggerDeploy={handleTriggerDeploy}
            />
          )}

          {currentTab === 'create-application' && (
            <CreateApplicationPage
              onBack={() => setCurrentTab('applications')}
              onSuccess={(app) => {
                setCurrentTab('applications');
                setSelectedApp(app);
              }}
              onCreateApp={handleCreateApplication}
            />
          )}

          {currentTab === 'environments' && (
            <EnvironmentsPage
              environments={environments}
              loading={loading}
              onSelectEnvironment={() => {}}
            />
          )}

          {currentTab === 'deployments' && (
            <DeploymentsPage
              deployments={deployments}
              loading={loading}
              onRefresh={loadPlatformData}
            />
          )}

          {currentTab === 'infrastructure' && <InfrastructurePage />}

          {currentTab === 'monitoring' && <MonitoringPage />}

          {currentTab === 'activity' && <ActivityPage />}

          {currentTab === 'settings' && <SettingsPage />}
        </main>
      </div>

      {/* Slide-over Application Details Inspector */}
      <AppDetailDrawer
        app={selectedApp}
        onClose={() => setSelectedApp(null)}
        onTriggerDeploy={handleTriggerDeploy}
        deployments={deployments}
        health={
          overviewData?.service_health.find(
            (s) => s.service_name === selectedApp?.name
          ) || null
        }
      />

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          setIsCommandPaletteOpen(false);
        }}
      />
    </div>
  );
};
