import React, { useState, useEffect, useMemo } from 'react';
import {
  Clock,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  User,
  Box,
  Search,
  ArrowRight
} from 'lucide-react';
import { Activity } from '../types';
import { api } from '../services/api';

interface ActivityPageProps {
  onSelectApplication: (appName: string) => void;
}

export const ActivityPage: React.FC<ActivityPageProps> = ({ onSelectApplication }) => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [appSearch, setAppSearch] = useState('');
  const [timeFilter, setTimeFilter] = useState('all');

  const fetchActivities = async () => {
    setLoading(true);
    try {
      const data = await api.getActivity();
      setActivities(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, []);

  const filtered = useMemo(() => {
    return activities.filter((act) => {
      // Filter by target type
      if (filterType !== 'all' && act.target_type.toLowerCase() !== filterType.toLowerCase()) {
        return false;
      }

      // Filter by status
      if (filterStatus !== 'all' && act.status.toLowerCase() !== filterStatus.toLowerCase()) {
        return false;
      }

      // Filter by application search
      if (appSearch.trim() !== '') {
        const q = appSearch.toLowerCase();
        const matchTarget = act.target.toLowerCase().includes(q);
        const matchAction = act.action.toLowerCase().includes(q);
        const matchDetails = act.details ? act.details.toLowerCase().includes(q) : false;
        if (!matchTarget && !matchAction && !matchDetails) return false;
      }

      // Filter by time
      if (timeFilter !== 'all' && act.created_at) {
        const createdDate = new Date(act.created_at);
        const now = new Date();
        if (timeFilter === 'today') {
          const isToday =
            createdDate.getDate() === now.getDate() &&
            createdDate.getMonth() === now.getMonth() &&
            createdDate.getFullYear() === now.getFullYear();
          if (!isToday) return false;
        } else if (timeFilter === '7d') {
          const diffDays = (now.getTime() - createdDate.getTime()) / (1000 * 3600 * 24);
          if (diffDays > 7) return false;
        }
      }

      return true;
    });
  }, [activities, filterType, filterStatus, appSearch, timeFilter]);

  const handleRowClick = (act: Activity) => {
    // Extract target app name if possible
    let candidate = act.target;
    if (candidate.includes('/')) {
      candidate = candidate.split('/')[1] || candidate;
    }
    candidate = candidate.replace(/\s*\(.*\)/, '').trim();
    if (candidate) {
      onSelectApplication(candidate);
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 w-full min-w-0 font-mono">
      {/* Header */}
      <div className="pb-2 border-b border-zinc-800/80">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2 font-sans">
          Platform Activity Log
        </h1>
        <p className="text-xs text-zinc-400 mt-1 font-sans">
          Global audit trail of application events, rollouts, CI executions, and provisioning actions across DevForge.
        </p>
      </div>

      {/* Multi-Filter Bar (Requirement 13: application, event type, status, time) */}
      <div className="p-3 rounded-md border border-zinc-800 bg-[#121215] space-y-3">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Application Search */}
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by application or details..."
              value={appSearch}
              onChange={(e) => setAppSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Event Type Filter */}
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-zinc-500">Type:</span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none"
              >
                <option value="all">All Types</option>
                <option value="application">Application</option>
                <option value="repository">Repository</option>
                <option value="ci">CI / Pipeline</option>
                <option value="image">Container Image</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-zinc-500">Status:</span>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="warning">Warning</option>
              </select>
            </div>

            {/* Time Filter */}
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-zinc-500">Time:</span>
              <select
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
                className="bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none"
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="7d">Last 7 Days</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Timeline List */}
      <div className="border border-zinc-800 bg-[#121215] rounded-md divide-y divide-zinc-800/60 overflow-hidden text-xs">
        {loading ? (
          <div className="p-8 text-center text-zinc-500">
            Loading activity log...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">
            No activity events matched the selected filters.
          </div>
        ) : (
          filtered.map((act) => (
            <div
              key={act.id}
              onClick={() => handleRowClick(act)}
              className="p-3.5 hover:bg-zinc-800/40 cursor-pointer transition flex items-start gap-3 group"
            >
              <div className="mt-0.5 shrink-0">
                {act.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                {act.status === 'failed' && <XCircle className="w-4 h-4 text-rose-500" />}
                {act.status === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-white group-hover:text-emerald-400 transition">
                      {act.action}
                    </span>
                    <span className="text-zinc-600">•</span>
                    <span className="text-zinc-300 font-bold group-hover:text-emerald-300 transition">
                      {act.target}
                    </span>
                  </div>
                  <span className="text-[11px] text-zinc-500 shrink-0">
                    {act.created_at ? new Date(act.created_at).toLocaleString() : ''}
                  </span>
                </div>

                {act.details && (
                  <div className="text-zinc-400 text-[11px] mt-1 font-sans break-words">
                    {act.details}
                  </div>
                )}

                <div className="flex items-center gap-3 text-[10px] text-zinc-500 mt-2">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3 text-zinc-600" />
                    <span className="text-zinc-400">{act.actor}</span>
                  </span>
                  <span>Type: <span className="text-zinc-400 uppercase">{act.target_type}</span></span>
                  <span className="ml-auto text-emerald-400 opacity-0 group-hover:opacity-100 transition flex items-center gap-1">
                    <span>View application</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
