import React, { useState } from 'react';
import {
  ArrowLeft,
  Box,
  GitBranch,
  Server,
  Layers,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Terminal,
  Cpu
} from 'lucide-react';
import { Application } from '../types';

interface CreateApplicationPageProps {
  onBack: () => void;
  onSuccess: (app: Application) => void;
  onCreateApp: (data: any) => Promise<Application>;
}

export const CreateApplicationPage: React.FC<CreateApplicationPageProps> = ({
  onBack,
  onSuccess,
  onCreateApp
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [team, setTeam] = useState('Platform Engineering');
  const [description, setDescription] = useState('');
  
  // Runtime & Source
  const [runtimeTemplate, setRuntimeTemplate] = useState('python-fastapi');
  const [repoUrl, setRepoUrl] = useState('https://github.com/devforge-org/');
  const [branch, setBranch] = useState('main');

  // Environment & Sizing
  const [environment, setEnvironment] = useState('development');
  const [port, setPort] = useState(8000);
  const [replicas, setReplicas] = useState(2);
  const [resourceProfile, setResourceProfile] = useState<'standard' | 'micro' | 'high'>('standard');

  const templates = [
    {
      id: 'python-fastapi',
      name: 'Python FastAPI',
      runtimeStr: 'Python 3.12 (FastAPI)',
      defaultPort: 8000,
      desc: 'High-performance async microservice with automatic OpenAPI swagger docs',
      tag: 'FastAPI'
    },
    {
      id: 'react-vite',
      name: 'React + Vite',
      runtimeStr: 'Node.js 20 (Vite)',
      defaultPort: 80,
      desc: 'Client-side SPA with TypeScript, Tailwind CSS, and optimized Nginx container',
      tag: 'Frontend'
    },
    {
      id: 'go-microservice',
      name: 'Go Microservice',
      runtimeStr: 'Go 1.22',
      defaultPort: 8080,
      desc: 'Compiled lightweight binary with minimal memory footprint and fast boot',
      tag: 'Compiled'
    },
    {
      id: 'node-service',
      name: 'Node.js API',
      runtimeStr: 'Node.js 20',
      defaultPort: 3000,
      desc: 'Event-driven Express/Node REST backend service',
      tag: 'Node'
    }
  ];

  const handleTemplateSelect = (t: typeof templates[0]) => {
    setRuntimeTemplate(t.id);
    setPort(t.defaultPort);
    if (!name) {
      // Keep empty
    } else {
      setRepoUrl(`https://github.com/devforge-org/${name}`);
    }
  };

  const handleNameChange = (val: string) => {
    const slugified = val.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    setName(slugified);
    setRepoUrl(`https://github.com/devforge-org/${slugified}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Application name is required.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      const selectedTpl = templates.find((t) => t.id === runtimeTemplate);
      const app = await onCreateApp({
        name,
        description: description || `Self-serviced service created via DevForge IDP.`,
        team,
        runtime: selectedTpl?.runtimeStr || 'Python 3.12 (FastAPI)',
        repository_url: repoUrl,
        branch,
        environment,
        version: 'v1.0.0',
        port: Number(port),
        replicas: Number(replicas)
      });
      onSuccess(app);
    } catch (err: any) {
      setError(err.message || 'Failed to create application.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 pb-2 border-b border-zinc-800/80">
        <button
          onClick={onBack}
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Create Application
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Self-service a new microservice or web application with production defaults.
          </p>
        </div>
      </div>

      {/* Progress Steps Indicator */}
      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
        {[
          { num: 1, title: '1. Basics', desc: 'Name & Team' },
          { num: 2, title: '2. Runtime & Git', desc: 'Template & Repo' },
          { num: 3, title: '3. Environment', desc: 'Target & Sizing' }
        ].map((s) => (
          <button
            key={s.num}
            onClick={() => setStep(s.num as any)}
            className={`p-3 rounded border text-left transition ${
              step === s.num
                ? 'border-emerald-500/80 bg-[#141417] text-white'
                : step > s.num
                ? 'border-zinc-700 bg-[#101012] text-zinc-300'
                : 'border-zinc-800 bg-[#0c0c0e] text-zinc-500'
            }`}
          >
            <div className="font-semibold flex items-center justify-between">
              <span>{s.title}</span>
              {step > s.num && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
            </div>
            <div className="text-[11px] text-zinc-400 mt-0.5">{s.desc}</div>
          </button>
        ))}
      </div>

      {error && (
        <div className="p-3 rounded border border-rose-800/60 bg-rose-950/40 text-rose-300 text-xs flex items-center gap-2 font-mono">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Form (Left) & Live Manifest Preview (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form Container (7 cols) */}
        <div className="lg:col-span-7 border border-zinc-800 bg-[#121215] rounded-md p-5">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* STEP 1: Basic Info */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
                    <span>Application Name *</span>
                    <span className="text-[11px] font-mono text-zinc-500">lowercase, hyphenated</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. order-processing-api"
                    value={name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 font-mono"
                  />
                  <span className="text-[11px] text-zinc-500">
                    DNS slug: <code className="text-emerald-400 font-mono">{name || 'your-service'}.devforge.internal</code>
                  </span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Owner Team *
                  </label>
                  <select
                    value={team}
                    onChange={(e) => setTeam(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 focus:outline-none focus:border-zinc-600 font-mono"
                  >
                    <option value="Platform Engineering">Platform Engineering</option>
                    <option value="Payments Core">Payments Core</option>
                    <option value="Security & Identity">Security & Identity</option>
                    <option value="Data Engineering">Data Engineering</option>
                    <option value="Frontend Infrastructure">Frontend Infrastructure</option>
                    <option value="Supply Chain">Supply Chain</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Describe the service purpose, consumer contracts, or SLAs..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      if (!name) setError('Please enter an application name first.');
                      else {
                        setError(null);
                        setStep(2);
                      }
                    }}
                    className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold rounded transition"
                  >
                    Next: Runtime & Git →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Runtime & Git Source */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-200">
                    Select Starter Template
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {templates.map((t) => (
                      <button
                        type="button"
                        key={t.id}
                        onClick={() => handleTemplateSelect(t)}
                        className={`p-3 rounded border text-left transition flex flex-col justify-between ${
                          runtimeTemplate === t.id
                            ? 'border-emerald-500 bg-zinc-900 text-white'
                            : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700 text-zinc-300'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold text-xs text-white">{t.name}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                            {t.tag}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 mt-1 line-clamp-2">{t.desc}</p>
                        <div className="text-[10px] font-mono text-emerald-400 mt-2">
                          Default Port: :{t.defaultPort}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5 pt-2">
                  <label className="text-xs font-semibold text-zinc-200">
                    Git Repository URL
                  </label>
                  <div className="flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-zinc-500" />
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Default Branch
                  </label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="px-3 py-1.5 text-zinc-400 hover:text-white text-xs transition"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold rounded transition"
                  >
                    Next: Environment Target →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Environment Target & Sizing */}
            {step === 3 && (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Target Environment
                  </label>
                  <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                    {['development', 'staging', 'production'].map((env) => (
                      <button
                        type="button"
                        key={env}
                        onClick={() => setEnvironment(env)}
                        className={`p-2.5 rounded border text-center uppercase font-medium transition ${
                          environment === env
                            ? 'border-emerald-500 bg-zinc-900 text-white'
                            : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700'
                        }`}
                      >
                        {env}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-zinc-200">
                      Container Port
                    </label>
                    <input
                      type="number"
                      value={port}
                      onChange={(e) => setPort(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-zinc-200">
                      Instance Replicas
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={replicas}
                      onChange={(e) => setReplicas(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Compute Sizing Profile
                  </label>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    {[
                      { id: 'micro', label: 'Micro', cpu: '250m vCPU', mem: '256Mi' },
                      { id: 'standard', label: 'Standard', cpu: '500m vCPU', mem: '512Mi' },
                      { id: 'high', label: 'High Perf', cpu: '1000m vCPU', mem: '1024Mi' }
                    ].map((p) => (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => setResourceProfile(p.id as any)}
                        className={`p-2 rounded border text-left font-mono transition ${
                          resourceProfile === p.id
                            ? 'border-emerald-500 bg-zinc-900 text-white'
                            : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700'
                        }`}
                      >
                        <div className="font-semibold text-zinc-200">{p.label}</div>
                        <div className="text-[10px] text-zinc-500">{p.cpu}</div>
                        <div className="text-[10px] text-zinc-500">{p.mem}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-between border-t border-zinc-800">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="px-3 py-1.5 text-zinc-400 hover:text-white text-xs transition"
                  >
                    ← Back
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition shadow-sm disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isSubmitting ? 'Provisioning...' : 'Provision & Deploy Application'}</span>
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Live Manifest Preview (5 cols) */}
        <div className="lg:col-span-5 border border-zinc-800 bg-[#0e0e11] rounded-md p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold text-zinc-200 font-mono">devforge.yaml</span>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">Live Synthesis</span>
            </div>

            <pre className="mt-3 text-[11px] font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800 overflow-x-auto leading-relaxed">
{`schemaVersion: "v1"
name: "${name || 'untitled-service'}"
team: "${team}"
runtime: "${templates.find((t) => t.id === runtimeTemplate)?.runtimeStr || 'Python 3.12'}"

spec:
  port: ${port}
  replicas: ${replicas}
  resources:
    profile: "${resourceProfile}"

git:
  repo: "${repoUrl}"
  branch: "${branch}"

targetEnvironment:
  name: "${environment}"
  autoDeploy: true`}
            </pre>
          </div>

          <div className="mt-4 p-3 rounded bg-zinc-900/60 border border-zinc-800 text-[11px] text-zinc-400 font-mono space-y-1">
            <div className="text-zinc-300 font-semibold flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span>Automated Workflow Provisioning:</span>
            </div>
            <div>• Registers service in DevForge metadata store</div>
            <div>• Creates cluster routing ingress & health probes</div>
            <div>• Triggers immediate initial verification build</div>
          </div>
        </div>
      </div>
    </div>
  );
};
