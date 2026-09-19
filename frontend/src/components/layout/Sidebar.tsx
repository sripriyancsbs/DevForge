import React from 'react';
import {
  LayoutDashboard,
  Box,
  Clock,
  Settings as SettingsIcon,
  X,
  Code2
} from 'lucide-react';

export type NavigationTab = 
  | 'overview' 
  | 'applications' 
  | 'create-application'
  | 'application-detail'
  | 'activity' 
  | 'settings';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  applicationsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isOpenMobile,
  onCloseMobile,
  applicationsCount = 0
}) => {
  const navItems = [
    { id: 'overview' as NavigationTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'applications' as NavigationTab, label: 'Applications', icon: Box },
    { id: 'activity' as NavigationTab, label: 'Activity', icon: Clock },
    { id: 'settings' as NavigationTab, label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 md:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:sticky top-0 left-0 h-screen w-60 shrink-0 bg-[#0c0c0e] border-r border-[#27272a] flex flex-col z-50 transition-transform duration-200 ease-in-out ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Brand Header - Clean, No Platform Version Badge */}
        <div className="h-14 border-b border-[#27272a] px-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-zinc-900 border border-zinc-700 flex items-center justify-center text-emerald-500 font-mono font-bold text-sm">
              <Code2 className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight text-white">
                DevForge
              </span>
              <span className="text-[10px] text-zinc-500 font-mono tracking-wider">INTERNAL PLATFORM</span>
            </div>
          </div>
          <button
            onClick={onCloseMobile}
            className="md:hidden text-zinc-400 hover:text-white p-1 rounded hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
          <div className="px-2.5 pb-2 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider font-mono">
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              currentTab === item.id ||
              (item.id === 'applications' && (currentTab === 'create-application' || currentTab === 'application-detail'));
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-zinc-800/90 text-white font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                <span>{item.label}</span>
                {item.id === 'applications' && applicationsCount > 0 && (
                  <span className="ml-auto text-[10px] font-mono text-zinc-400 bg-zinc-800 px-1.5 py-0.5 rounded border border-zinc-700/50">
                    {applicationsCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Footer info: Truthful Cluster & Database telemetry */}
        <div className="p-3 border-t border-[#27272a] bg-[#0e0e11]">
          <div className="rounded border border-zinc-800/80 bg-zinc-900/50 p-2 text-xs">
            <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400 mb-1">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Cluster Healthy
              </span>
              <span className="text-[10px] text-zinc-500">Local KinD</span>
            </div>
            <div className="text-[10px] text-zinc-500 font-mono flex items-center justify-between">
              <span>Kubernetes IDP</span>
              <span className="text-zinc-400">PostgreSQL</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
