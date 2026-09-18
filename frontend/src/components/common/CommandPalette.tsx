import React, { useState, useEffect } from 'react';
import { Search, Box, Server, GitCommit, Plus, ArrowRight, X } from 'lucide-react';
import { NavigationTab } from '../layout/Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTab: (tab: NavigationTab) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectTab
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    { label: 'Create New Application', tab: 'create-application' as NavigationTab, icon: Plus, hint: 'Provision a new service' },
    { label: 'View All Applications', tab: 'applications' as NavigationTab, icon: Box, hint: '8 services registered' },
    { label: 'View Active Environments', tab: 'environments' as NavigationTab, icon: Server, hint: 'Prod, Staging, Dev, Preview' },
    { label: 'Deployment Pipeline', tab: 'deployments' as NavigationTab, icon: GitCommit, hint: 'Recent rollouts and build logs' },
    { label: 'Platform Overview', tab: 'overview' as NavigationTab, icon: Box, hint: 'Metrics, health & activity' },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(query.toLowerCase()) ||
    a.hint.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/75 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg rounded-lg border border-zinc-800 bg-[#121215] shadow-2xl overflow-hidden animate-in fade-in-0 zoom-in-95 duration-100">
        <div className="flex items-center gap-2 px-3 py-2.5 border-b border-zinc-800">
          <Search className="w-4 h-4 text-zinc-500 shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder="Type a command or jump to page..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none font-mono"
          />
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-2 max-h-72 overflow-y-auto space-y-1">
          {filtered.length === 0 ? (
            <div className="py-6 text-center text-xs text-zinc-500 font-mono">
              No matching platform actions found.
            </div>
          ) : (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  onClick={() => {
                    onSelectTab(item.tab);
                    onClose();
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-md hover:bg-zinc-800 text-left transition text-xs group"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded bg-zinc-800/80 border border-zinc-700/60 text-zinc-300">
                      <Icon className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div>
                      <div className="font-medium text-zinc-200">{item.label}</div>
                      <div className="text-[11px] text-zinc-500">{item.hint}</div>
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-300 transition" />
                </button>
              );
            })
          )}
        </div>

        <div className="px-3 py-2 bg-zinc-900/60 border-t border-zinc-800 text-[10px] text-zinc-500 font-mono flex items-center justify-between">
          <span>Navigate with arrows, select with Enter</span>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  );
};
