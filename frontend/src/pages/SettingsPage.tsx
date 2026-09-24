import React, { useState, useEffect } from 'react';
import {
  Key,
  Shield,
  GitBranch,
  Database,
  Check,
  Server,
  Terminal,
  Lock,
  UserCheck,
  Users,
  Layers,
  Plus,
  UserPlus,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { getAuthToken, getStoredUser, api, getActiveWorkspaceId } from '../services/api';
import { Workspace, WorkspaceMember } from '../types';

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'workspace' | 'members' | 'security' | 'account'>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const t = params.get('tab');
      if (t === 'members' || t === 'security' || t === 'account' || t === 'workspace') {
        return t;
      }
    }
    return 'members';
  });

  const [copiedKey, setCopiedKey] = useState(false);
  const [currentUser, setCurrentUser] = useState(getStoredUser());
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Add Member Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newConfirmPassword, setNewConfirmPassword] = useState('');
  const [newRole, setNewRole] = useState<'ADMIN' | 'OPERATOR' | 'DEVELOPER' | 'VIEWER'>('DEVELOPER');
  const [submittingMember, setSubmittingMember] = useState(false);

  const activeWsId = getActiveWorkspaceId();
  const sessionToken = getAuthToken() || (currentUser ? `df_jwt_session_${currentUser.username}_active` : '');
  const isAdmin = currentUser?.role === 'ADMIN';

  const copyToken = () => {
    navigator.clipboard?.writeText(sessionToken);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const loadWorkspaceData = async () => {
    try {
      const ws = await api.getCurrentWorkspace();
      setWorkspace(ws);
    } catch (err) {
      console.error('Failed to load workspace:', err);
    }
  };

  const loadMembers = async () => {
    setLoadingMembers(true);
    setActionError(null);
    try {
      const data = await api.getWorkspaceMembers(activeWsId);
      setMembers(data);
    } catch (err: any) {
      setActionError(err.message || 'Failed to load workspace members.');
    } finally {
      setLoadingMembers(false);
    }
  };

  useEffect(() => {
    api.getCurrentUser()
      .then((u) => setCurrentUser(u))
      .catch(() => {});
    loadWorkspaceData();
    loadMembers();
  }, [activeWsId]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail.trim()) {
      setActionError('Email address is required.');
      return;
    }
    if (newPassword && newPassword.length < 8) {
      setActionError('Password must be at least 8 characters long.');
      return;
    }
    if (newPassword && newPassword !== newConfirmPassword) {
      setActionError('Passwords do not match.');
      return;
    }

    setSubmittingMember(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await api.addWorkspaceMember(activeWsId, {
        email: newEmail.trim(),
        name: newName.trim() || undefined,
        username: newUsername.trim() || undefined,
        display_name: newDisplayName.trim() || newName.trim() || undefined,
        password: newPassword || undefined,
        confirm_password: newConfirmPassword || undefined,
        role: newRole
      });
      setActionSuccess(`Successfully created user ${newEmail.trim()} with role ${newRole}.`);
      setShowAddModal(false);
      setNewName('');
      setNewEmail('');
      setNewUsername('');
      setNewDisplayName('');
      setNewPassword('');
      setNewConfirmPassword('');
      setNewRole('DEVELOPER');
      await loadMembers();
      await loadWorkspaceData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to add workspace member.');
    } finally {
      setSubmittingMember(false);
    }
  };

  const handleRoleChange = async (memberId: number, targetRole: string) => {
    setActionError(null);
    setActionSuccess(null);
    try {
      await api.updateWorkspaceMemberRole(activeWsId, memberId, targetRole);
      setActionSuccess(`Role updated to ${targetRole}.`);
      await loadMembers();
    } catch (err: any) {
      setActionError(err.message || 'Failed to update member role.');
    }
  };

  const handleDisableMember = async (memberId: number, memberName: string) => {
    if (!window.confirm(`Are you sure you want to disable member ${memberName}?`)) {
      return;
    }
    setActionError(null);
    setActionSuccess(null);
    try {
      await api.disableWorkspaceMember(activeWsId, memberId);
      setActionSuccess(`Member ${memberName} disabled.`);
      await loadMembers();
    } catch (err: any) {
      setActionError(err.message || 'Failed to disable member.');
    }
  };

  const handleDeleteMember = async (memberId: number, memberName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete user ${memberName}? This action cannot be undone.`)) {
      return;
    }
    setActionError(null);
    setActionSuccess(null);
    try {
      await api.deleteWorkspaceMember(activeWsId, memberId, true);
      setActionSuccess(`Member ${memberName} deleted.`);
      await loadMembers();
      await loadWorkspaceData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete member.');
    }
  };

  if (!currentUser) {
    return (
      <div className="p-8 text-center text-xs font-mono text-zinc-400">
        Authentication required to access platform settings.
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6 w-full min-w-0">
      {/* Header */}
      <div className="pb-3 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Platform Settings
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Workspace management, members, security controls, and runtime configuration.
          </p>
        </div>

        {/* Workspace Context Chip */}
        <div className="flex items-center gap-2 text-xs font-mono bg-[#141417] px-3 py-1.5 rounded border border-zinc-800 text-zinc-300 self-start sm:self-auto">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Workspace: <strong className="text-white">{workspace?.slug || 'default-workspace'}</strong></span>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-zinc-800 space-x-1 sm:space-x-4 overflow-x-auto text-xs font-medium">
        <button
          id="settings-tab-workspace"
          data-testid="settings-tab-workspace"
          onClick={() => setActiveTab('workspace')}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
            activeTab === 'workspace'
              ? 'border-emerald-500 text-emerald-400 font-semibold'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Workspace</span>
        </button>

        <button
          id="settings-tab-members"
          data-testid="settings-tab-members"
          onClick={() => setActiveTab('members')}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
            activeTab === 'members'
              ? 'border-emerald-500 text-emerald-400 font-semibold'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Members</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
            {members.length}
          </span>
        </button>

        <button
          id="settings-tab-security"
          data-testid="settings-tab-security"
          onClick={() => setActiveTab('security')}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
            activeTab === 'security'
              ? 'border-emerald-500 text-emerald-400 font-semibold'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>Security</span>
        </button>

        <button
          id="settings-tab-account"
          data-testid="settings-tab-account"
          onClick={() => setActiveTab('account')}
          className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition cursor-pointer whitespace-nowrap ${
            activeTab === 'account'
              ? 'border-emerald-500 text-emerald-400 font-semibold'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Account</span>
        </button>
      </div>

      {/* Global Status Alerts */}
      {actionError && (
        <div id="settings-action-error" className="p-3 rounded bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}
      {actionSuccess && (
        <div id="settings-action-success" className="p-3 rounded bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* TAB 1: MEMBERS MANAGEMENT (Phase 14 Core) */}
      {activeTab === 'members' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                Workspace Members
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Manage user access, role assignments, and member status for <strong>{workspace?.name || 'Default Workspace'}</strong>.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={loadMembers}
                className="p-1.5 rounded border border-zinc-800 text-zinc-400 hover:text-zinc-200 bg-zinc-900/60 transition cursor-pointer"
                title="Refresh Members"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingMembers ? 'animate-spin' : ''}`} />
              </button>

              {isAdmin ? (
                <button
                  id="add-member-button"
                  data-testid="add-member-button"
                  onClick={() => setShowAddModal(true)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded text-xs font-medium transition flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Add Member</span>
                </button>
              ) : (
                <span className="text-[11px] font-mono text-zinc-500 bg-zinc-900/60 px-2.5 py-1 rounded border border-zinc-800">
                  Read-only view (Admin required for modifications)
                </span>
              )}
            </div>
          </div>

          {/* Members Table */}
          <div className="rounded-md border border-zinc-800 bg-[#121215] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-[#18181b] border-b border-zinc-800 text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">User</th>
                    <th className="py-2.5 px-4 font-medium">Email</th>
                    <th className="py-2.5 px-4 font-medium">Role</th>
                    <th className="py-2.5 px-4 font-medium">Status</th>
                    <th className="py-2.5 px-4 font-medium">Joined</th>
                    <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {members.map((m) => {
                    const isSelf = m.user_id === currentUser.id;
                    return (
                      <tr
                        key={m.id}
                        id={`member-row-${m.id}`}
                        data-testid="member-row"
                        className="hover:bg-zinc-900/40 transition"
                      >
                        <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                          <div className="w-6 h-6 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-mono font-semibold text-zinc-300 uppercase shrink-0">
                            {(m.display_name || m.username || 'U').slice(0, 2)}
                          </div>
                          <div className="truncate">
                            <div>{m.display_name || m.username}</div>
                            {m.username && m.display_name && (
                              <div className="text-[10px] font-mono text-zinc-500">@{m.username}</div>
                            )}
                          </div>
                          {isSelf && (
                            <span className="text-[9px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.2 rounded ml-1">
                              You
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 font-mono text-zinc-400">
                          {m.email || '—'}
                        </td>

                        <td className="py-3 px-4">
                          {isAdmin && !isSelf ? (
                            <select
                              id={`member-role-select-${m.id}`}
                              data-testid={`member-role-select-${m.id}`}
                              value={m.role}
                              onChange={(e) => handleRoleChange(m.id, e.target.value)}
                              className="bg-zinc-950 border border-zinc-800 text-zinc-200 text-xs rounded px-2 py-1 font-mono focus:outline-none focus:border-zinc-600"
                            >
                              <option value="VIEWER">VIEWER</option>
                              <option value="DEVELOPER">DEVELOPER</option>
                              <option value="OPERATOR">OPERATOR</option>
                              <option value="ADMIN">ADMIN</option>
                            </select>
                          ) : (
                            <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-semibold ${
                              m.role === 'ADMIN'
                                ? 'text-violet-400 bg-violet-950/60 border-violet-800/60'
                                : m.role === 'OPERATOR'
                                ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60'
                                : m.role === 'DEVELOPER'
                                ? 'text-amber-400 bg-amber-950/60 border-amber-800/60'
                                : 'text-zinc-400 bg-zinc-800 border-zinc-700'
                            }`}>
                              {m.role}
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                            m.status === 'active'
                              ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60'
                              : 'text-zinc-400 bg-zinc-900 border-zinc-800'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${m.status === 'active' ? 'bg-emerald-500' : 'bg-zinc-500'}`} />
                            {m.status}
                          </span>
                        </td>

                        <td className="py-3 px-4 text-zinc-500 font-mono text-[11px]">
                          {m.created_at ? new Date(m.created_at).toLocaleDateString() : '—'}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2.5">
                            {isAdmin && !isSelf && m.status === 'active' && (
                              <button
                                id={`disable-member-btn-${m.id}`}
                                data-testid={`disable-member-btn-${m.id}`}
                                onClick={() => handleDisableMember(m.id, m.display_name || m.username || 'member')}
                                className="text-amber-400 hover:text-amber-300 text-xs font-mono hover:underline cursor-pointer"
                              >
                                Disable
                              </button>
                            )}
                            {m.status === 'disabled' && (
                              <span className="text-zinc-500 font-mono text-[11px]">Disabled</span>
                            )}
                            {isAdmin && !isSelf && (
                              <button
                                id={`delete-member-btn-${m.id}`}
                                data-testid={`delete-member-btn-${m.id}`}
                                onClick={() => handleDeleteMember(m.id, m.display_name || m.username || 'member')}
                                className="text-rose-400 hover:text-rose-300 text-xs font-mono hover:underline cursor-pointer"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {members.length === 0 && !loadingMembers && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-zinc-500 font-mono text-xs">
                        No members found in this workspace.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Member Modal */}
          {showAddModal && (
            <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
              <div className="bg-[#141417] border border-zinc-800 rounded-lg max-w-md w-full p-5 space-y-4 shadow-2xl">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <UserPlus className="w-4 h-4 text-emerald-400" />
                    Create User / Add Member
                  </h3>
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="text-zinc-400 hover:text-zinc-200 text-sm font-mono"
                  >
                    ✕
                  </button>
                </div>

                <form onSubmit={handleAddMember} className="space-y-3 text-xs">
                  <div>
                    <label className="block text-zinc-300 font-medium mb-1 font-mono">
                      Full Name <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="add-member-name-input"
                      data-testid="add-member-name-input"
                      type="text"
                      required
                      placeholder="Jane Doe"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-300 font-medium mb-1 font-mono">
                      Email Address <span className="text-rose-400">*</span>
                    </label>
                    <input
                      id="add-member-email-input"
                      data-testid="add-member-email-input"
                      type="email"
                      required
                      placeholder="jane@devforge.com"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-zinc-300 font-medium mb-1 font-mono">
                        Password <span className="text-rose-400">*</span>
                      </label>
                      <input
                        id="add-member-password-input"
                        data-testid="add-member-password-input"
                        type="password"
                        required
                        placeholder="••••••••"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="block text-zinc-300 font-medium mb-1 font-mono">
                        Confirm Password <span className="text-rose-400">*</span>
                      </label>
                      <input
                        id="add-member-confirmpassword-input"
                        data-testid="add-member-confirmpassword-input"
                        type="password"
                        required
                        placeholder="••••••••"
                        value={newConfirmPassword}
                        onChange={(e) => setNewConfirmPassword(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-zinc-300 font-medium mb-1 font-mono">
                      Assigned Role
                    </label>
                    <select
                      id="add-member-role-select"
                      data-testid="add-member-role-select"
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value as any)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    >
                      <option value="VIEWER">VIEWER — Read-only catalog, activity, and telemetry</option>
                      <option value="DEVELOPER">DEVELOPER — Create applications, scaffold templates</option>
                      <option value="OPERATOR">OPERATOR — Deploy, rollbacks, and remediation approval</option>
                      <option value="ADMIN">ADMIN — Full workspace membership and security governance</option>
                    </select>
                  </div>

                  <div className="pt-2 border-t border-zinc-800 flex items-center justify-end gap-2">
                    <button
                      id="add-member-cancel-button"
                      type="button"
                      onClick={() => setShowAddModal(false)}
                      className="px-3 py-1.5 rounded border border-zinc-800 text-zinc-400 hover:text-zinc-200 bg-zinc-900 transition font-mono"
                    >
                      Cancel
                    </button>
                    <button
                      id="add-member-submit-button"
                      data-testid="add-member-submit-button"
                      type="submit"
                      disabled={submittingMember}
                      className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition flex items-center gap-1.5 font-mono cursor-pointer disabled:opacity-50"
                    >
                      {submittingMember ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                      <span>Create User</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: WORKSPACE DETAILS */}
      {activeTab === 'workspace' && (
        <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
            <div className="flex items-center gap-2.5">
              <Layers className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-white">Active Workspace Configuration</h2>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 uppercase">
              {workspace?.status || 'active'}
            </span>
          </div>

          <p className="text-xs text-zinc-400 leading-relaxed">
            Workspaces provide strict multi-tenant boundary isolation across applications, members, deployments, and audit logs.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Workspace Name</span>
              <div className="text-zinc-200 mt-1 font-semibold">{workspace?.name || 'Default Workspace'}</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Identifier / Slug</span>
              <div className="text-emerald-400 mt-1 font-semibold">{workspace?.slug || 'default-workspace'}</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Total Members</span>
              <div className="text-zinc-200 mt-1 font-semibold">{members.length} members</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Your Workspace Role</span>
              <div className="text-zinc-200 mt-1 font-semibold">{currentUser.role}</div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SECURITY CONTROLS */}
      {activeTab === 'security' && (
        <div className="space-y-5">
          {/* Bearer Token */}
          <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5">
                <Key className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-semibold text-white">Active Session Bearer Token</h2>
              </div>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              JWT Bearer token generated for current authenticated identity ({currentUser.username}). Pass as Authorization header.
            </p>
            <div className="flex items-center gap-2">
              <input
                id="session-token-input"
                type="password"
                readOnly
                value={sessionToken}
                className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs font-mono text-zinc-300 focus:outline-none"
              />
              <button
                id="copy-token-button"
                onClick={copyToken}
                className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-mono rounded border border-zinc-700 transition flex items-center gap-1.5 cursor-pointer"
              >
                {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Terminal className="w-3.5 h-3.5" />}
                <span>{copiedKey ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Database Engine */}
          <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5">
                <Server className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-semibold text-white">PostgreSQL Multi-User Database</h2>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                PostgreSQL 16 Active
              </span>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              All identity records, workspace memberships, and RBAC rules are persistently governed by PostgreSQL tables with foreign key constraints.
            </p>
          </div>

          {/* Security Hardening Checklist */}
          <div className="rounded-md border border-zinc-800/60 bg-[#0e0e11] p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                Production Security Hardening (Phase 12-14)
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded">
                Hardened
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono text-zinc-400">
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ Workspace Boundary Isolation
              </div>
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ Non-root Container Isolation
              </div>
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ PBKDF2-SHA256 (600k rounds)
              </div>
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ In-Memory Sliding Rate Limit
              </div>
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ Zero Self-Service Role Forgery
              </div>
              <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-800/40">
                ✓ Cross-Tenant IDOR Protection
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ACCOUNT DETAILS */}
      {activeTab === 'account' && (
        <div className="rounded-md border border-zinc-800 bg-[#121215] p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
            <div className="flex items-center gap-2.5">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-white">Your Authenticated Profile</h2>
            </div>
            <span className={`text-[11px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${
              currentUser.role === 'ADMIN'
                ? 'text-violet-400 bg-violet-950/60 border-violet-800/60'
                : currentUser.role === 'OPERATOR'
                ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60'
                : currentUser.role === 'DEVELOPER'
                ? 'text-amber-400 bg-amber-950/60 border-amber-800/60'
                : 'text-zinc-400 bg-zinc-800 border-zinc-700'
            }`}>
              Role: {currentUser.role}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Display Name</span>
              <div className="text-zinc-200 mt-1 font-semibold">{currentUser.display_name || currentUser.username}</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Email</span>
              <div className="text-zinc-200 mt-1 font-semibold">{currentUser.email}</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Active Workspace</span>
              <div className="text-emerald-400 mt-1 font-semibold">{workspace?.slug || 'default-workspace'}</div>
            </div>
            <div className="p-3 rounded bg-zinc-950 border border-zinc-800">
              <span className="text-zinc-500 text-[10px] uppercase">Assigned Permissions</span>
              <div className="text-zinc-400 mt-1 text-[11px] truncate">
                {currentUser.permissions?.join(', ') || 'view:all'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
