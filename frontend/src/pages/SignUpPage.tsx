import React, { useState } from 'react';
import { Lock, Mail, User as UserIcon, ArrowRight, AlertCircle, Loader2, Code2, Check, X, Shield } from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface SignUpPageProps {
  onSuccess: (user: User) => void;
  onNavigateToSignIn: () => void;
}

export const SignUpPage: React.FC<SignUpPageProps> = ({ onSuccess, onNavigateToSignIn }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordsMatch = password.length > 0 && confirmPassword.length > 0 && password === confirmPassword;
  const passwordLongEnough = password.length >= 8;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setError('Please provide your full name.');
      return;
    }
    if (!email.trim() || !email.includes('@') || !email.split('@')[1]?.includes('.')) {
      setError('Please enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.signup({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword
      });
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Failed to register account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#f4f4f5] flex items-center justify-center p-4 sm:p-6 select-none relative overflow-hidden" data-testid="signup-page">
      {/* Ambient background lighting */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-[350px] h-[350px] bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 text-cyan-400 shadow-xl mb-1">
            <Code2 className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white font-mono">Create an account</h1>
          <p className="text-xs text-zinc-400">Join DevForge Internal Developer Platform</p>
        </div>

        {/* Card Container */}
        <div id="signup-card" data-testid="signup-card" className="bg-[#121215]/90 border border-zinc-800/90 rounded-xl p-6 sm:p-8 shadow-2xl backdrop-blur-md space-y-5">
          {error && (
            <div
              id="signup-error-banner"
              data-testid="signup-error-banner"
              className="p-3 rounded-md bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2.5 animate-in fade-in duration-150"
            >
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span className="font-sans">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5 font-mono">
                <UserIcon className="w-3.5 h-3.5 text-zinc-400" />
                <span>Full Name</span>
              </label>
              <input
                id="signup-name-input"
                data-testid="signup-name-input"
                type="text"
                required
                placeholder="e.g. Alex Morgan"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-500 transition shadow-inner"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5 font-mono">
                <Mail className="w-3.5 h-3.5 text-zinc-400" />
                <span>Email Address</span>
              </label>
              <input
                id="signup-email-input"
                data-testid="signup-email-input"
                type="email"
                required
                placeholder="alex@company.internal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-500 transition shadow-inner"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Password</span>
                </span>
                <span className="text-[10px] text-zinc-500 font-sans">Min 8 chars</span>
              </label>
              <input
                id="signup-password-input"
                data-testid="signup-password-input"
                type="password"
                required
                placeholder="Create a strong password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-500 transition shadow-inner"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-300 flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Confirm Password</span>
                </span>
              </label>
              <input
                id="signup-confirm-password-input"
                data-testid="signup-confirm-password-input"
                type="password"
                required
                placeholder="Repeat your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-cyan-500 transition shadow-inner"
              />
            </div>

            {/* Micro Validation Badges */}
            <div className="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 space-y-1 text-[11px] font-mono">
              <div className={`flex items-center gap-1.5 ${passwordLongEnough ? 'text-emerald-400' : 'text-zinc-500'}`}>
                {passwordLongEnough ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                <span>At least 8 characters</span>
              </div>
              <div className={`flex items-center gap-1.5 ${passwordsMatch ? 'text-emerald-400' : 'text-zinc-500'}`}>
                {passwordsMatch ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                <span>Passwords match</span>
              </div>
              <div className="flex items-center gap-1.5 text-zinc-400 pt-1 border-t border-zinc-800/60 text-[10px]">
                <Shield className="w-3 h-3 text-cyan-400 shrink-0" />
                <span>Default role: <strong className="text-zinc-200">DEVELOPER</strong> (governed by workspace policy)</span>
              </div>
            </div>

            <button
              id="signup-submit-btn"
              data-testid="signup-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition shadow-lg shadow-cyan-950/40 flex items-center justify-center gap-2 cursor-pointer font-mono"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Link to Sign In */}
        <div className="text-center text-xs text-zinc-400 font-sans">
          Already have an account?{' '}
          <button
            id="signup-to-signin-link"
            data-testid="signup-to-signin-link"
            onClick={onNavigateToSignIn}
            className="text-cyan-400 hover:text-cyan-300 font-medium underline underline-offset-2 transition cursor-pointer"
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
};
