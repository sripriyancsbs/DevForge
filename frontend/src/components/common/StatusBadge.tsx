import React from 'react';
import { StateStatus } from '../../types';

interface StatusBadgeProps {
  status: StateStatus | string;
  size?: 'sm' | 'md';
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm', pulse = false }) => {
  const norm = (status || '').toLowerCase();

  let dotColor = 'bg-zinc-400';
  let badgeColor = 'bg-zinc-800/80 text-zinc-300 border-zinc-700/50';
  let label = status;

  if (norm === 'healthy' || norm === 'completed' || norm === 'success' || norm === 'active') {
    dotColor = 'bg-emerald-500';
    badgeColor = 'bg-emerald-950/40 text-emerald-400 border-emerald-800/40';
    label = norm === 'completed' ? 'Completed' : 'Healthy';
  } else if (norm === 'warning' || norm === 'degraded') {
    dotColor = 'bg-amber-500';
    badgeColor = 'bg-amber-950/40 text-amber-400 border-amber-800/40';
    label = norm === 'degraded' ? 'Degraded' : 'Warning';
  } else if (norm === 'failed' || norm === 'error') {
    dotColor = 'bg-rose-500';
    badgeColor = 'bg-rose-950/40 text-rose-400 border-rose-800/40';
    label = 'Failed';
  } else if (norm === 'deploying' || norm === 'building' || norm === 'running') {
    dotColor = 'bg-sky-400';
    badgeColor = 'bg-sky-950/40 text-sky-400 border-sky-800/40';
    label = norm === 'building' ? 'Building' : 'Deploying';
    pulse = true;
  } else if (norm === 'rolled_back') {
    dotColor = 'bg-zinc-400';
    badgeColor = 'bg-zinc-800/80 text-zinc-300 border-zinc-700/50';
    label = 'Rolled Back';
  } else if (norm === 'pending') {
    dotColor = 'bg-zinc-500';
    badgeColor = 'bg-zinc-800/80 text-zinc-400 border-zinc-700/50';
    label = 'Pending';
  }

  const sizeClasses = size === 'sm' 
    ? 'px-2 py-0.5 text-xs font-mono' 
    : 'px-2.5 py-1 text-xs font-mono';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded border ${badgeColor} ${sizeClasses} font-medium`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor} ${pulse ? 'animate-pulse' : ''}`} />
      <span className="capitalize">{label}</span>
    </span>
  );
};
