import React, { useState } from 'react';
import { Lock, Mail, ArrowRight, AlertCircle, Loader2, ShieldCheck, Code2, Eye, EyeOff } from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface SignInPageProps {
  onSuccess: (user: User) => void;
  onNavigateToSignUp: () => void;
}

export const SignInPage: React.FC<SignInPageProps> = ({ onSuccess, onNavigateToSignUp }) => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) {
      setError('Please enter your email or username.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.login(identifier.trim(), password);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (email: string, pass: string) => {
    setIdentifier(email);
    setPassword(pass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex items-center justify-center p-4 sm:p-6 select-none relative overflow-hidden" data-testid="signin-page">
      {/* Background ambient lighting */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[350px] h-[350px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 text-emerald-400 shadow-xl mb-1">
            <Code2 className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white font-mono">Sign in to DevForge</h1>
          <p className="text-xs text-zinc-400">Internal Developer Platform • Kubernetes & Cloud Workspaces</p>
        </div>

        {/* Card Container */}
        <div id="signin-card" data-testid="signin-card" className="bg-[#121215]/90 border border-zinc-800/90 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-md space-y-5">
          {error && (
            <div
              id="signin-error-banner"
              data-testid="signin-error-banner"
              className="p-3 rounded-md bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2.5 animate-in fade-in duration-150"
            >
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span className="font-sans">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5 font-mono">
                <Mail className="w-3.5 h-3.5 text-zinc-400" />
                <span>Email or Username</span>
              </label>
              <input
                id="signin-email-input"
                data-testid="signin-email-input"
                type="text"
                autoComplete="username"
                required
                placeholder="name@devforge.internal or admin"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-emerald-500 transition shadow-inner"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Password</span>
                </span>
                <span className="text-[10px] text-zinc-500">Secure PBKDF2</span>
              </label>
              <div className="relative">
                <input
                  id="signin-password-input"
                  data-testid="signin-password-input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  placeholder="Enter your account password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-3.5 pr-10 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-emerald-500 transition shadow-inner"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 p-0.5"
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              id="signin-submit-btn"
              data-testid="signin-submit-btn"
              name="auth-form-submit-button"
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-lg shadow-emerald-950/40 flex items-center justify-center gap-2 cursor-pointer font-mono"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Console</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Single Bootstrap Administrator hint */}
          <div className="pt-3 border-t border-zinc-800/80 space-y-2">
            <div className="text-[11px] font-mono text-zinc-500 flex items-center justify-between">
              <span>Default Administrator:</span>
              <ShieldCheck className="w-3 h-3 text-zinc-500" />
            </div>
            <button
              type="button"
              id="bootstrap-admin-fill"
              data-testid="bootstrap-admin-fill"
              onClick={() => handleQuickFill('admin@devforge.com', 'pass123')}
              className="w-full p-2 rounded bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 border border-zinc-800 text-left transition font-mono text-[11px] cursor-pointer flex items-center justify-between"
            >
              <span>👑 <strong className="text-violet-400">ADMIN</strong> (admin@devforge.com)</span>
              <span className="text-[10px] text-zinc-500">Quick Fill</span>
            </button>
          </div>
        </div>

        {/* Link to Sign Up */}
        <div className="text-center text-xs text-zinc-400 font-sans">
          Don't have an account?{' '}
          <button
            id="signin-to-signup-link"
            data-testid="signin-to-signup-link"
            onClick={onNavigateToSignUp}
            className="text-emerald-400 hover:text-emerald-300 font-medium underline underline-offset-2 transition cursor-pointer"
          >
            Create an account
          </button>
        </div>
      </div>
    </div>
  );
};
