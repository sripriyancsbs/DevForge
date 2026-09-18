import React, { useState, useEffect } from 'react';
import { Clock, Filter, CheckCircle2, AlertTriangle, XCircle, User, Box } from 'lucide-react';
import { Activity } from '../types';
import { api } from '../services/api';

export const ActivityPage: React.FC = () => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [filterType, setFilterType] = useState('all');

  useEffect(() => {
    api.getActivity().then(setActivities).catch(console.error);
  }, []);

  const filtered = activities.filter((a) => {
    if (filterType === 'all') return true;
    return a.target_type === filterType;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          Platform Activity Log
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Immutable audit trail of service deployments, configuration updates, and infrastructure events.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3 p-3 rounded-md border border-zinc-800 bg-[#121215] text-xs">
        <span className="text-zinc-400 font-mono flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter by target:</span>
        </span>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 font-mono focus:outline-none"
        >
          <option value="all">All Event Types</option>
          <option value="application">Applications</option>
          <option value="environment">Environments</option>
          <option value="deployment">Deployments</option>
        </select>
      </div>

      {/* Activity Timeline List */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md divide-y divide-zinc-800/60 overflow-hidden font-mono text-xs">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            No activity events recorded.
          </div>
        ) : (
          filtered.map((act) => (
            <div key={act.id} className="p-4 hover:bg-zinc-800/30 transition flex items-start gap-3">
              <div className="mt-0.5">
                {act.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                {act.status === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                {act.status === 'failed' && <XCircle className="w-4 h-4 text-rose-500" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{act.action}</span>
                    <span className="text-zinc-500">•</span>
                    <span className="text-zinc-300 font-bold">{act.target}</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    {new Date(act.created_at).toLocaleString()}
                  </span>
                </div>

                {act.details && (
                  <div className="text-zinc-400 text-[11px] mt-1">
                    {act.details}
                  </div>
                )}

                <div className="flex items-center gap-3 text-[10px] text-zinc-500 mt-2">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3 text-zinc-600" />
                    <span className="text-zinc-400">{act.actor}</span>
                  </span>
                  <span>Type: <span className="text-zinc-400 uppercase">{act.target_type}</span></span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
