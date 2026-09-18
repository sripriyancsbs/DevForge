import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Server,
  CheckCircle2,
  AlertCircle,
  FileCode,
  FolderTree,
  Database,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Check,
  Loader2,
  XCircle,
  RotateCw,
  GitBranch,
  Github
} from 'lucide-react';
import { api } from '../services/api';
import { Application, ApplicationProvisioningResponse, ProvisioningJob, ProvisioningJobStep } from '../types';

interface CreateApplicationPageProps {
  onBack: () => void;
  onSuccess: (app: Application) => void;
  onCreateApp: (data: any) => Promise<ApplicationProvisioningResponse>;
}

export const CreateApplicationPage: React.FC<CreateApplicationPageProps> = ({
  onBack,
  onSuccess,
  onCreateApp
}) => {
  const [stage, setStage] = useState<'wizard' | 'provisioning' | 'ready' | 'failed'>('wizard');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [currentJob, setCurrentJob] = useState<ProvisioningJob | null>(null);
  const [provisionResult, setProvisionResult] = useState<ApplicationProvisioningResponse | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [team, setTeam] = useState('Platform Engineering');
  const [description, setDescription] = useState('');
  const [gitHubOwner, setGitHubOwner] = useState('sripriyancsbs');

  useEffect(() => {
    api.getGitHubStatus()
      .then((res) => {
        if (res && res.owner) setGitHubOwner(res.owner);
      })
      .catch(() => {});
  }, []);
  
  // Runtime & Source
  const [runtimeTemplate, setRuntimeTemplate] = useState('python-fastapi');
  const [repoUrl, setRepoUrl] = useState(`https://github.com/${gitHubOwner}/`);
  const [branch, setBranch] = useState('main');

  // Environment & Sizing
  const [environment, setEnvironment] = useState('development');
  const [port, setPort] = useState(8000);
  const [replicas, setReplicas] = useState(2);
  const [databaseType, setDatabaseType] = useState('none');
  const [deploymentStrategy, setDeploymentStrategy] = useState('rolling');
  const [resourceProfile, setResourceProfile] = useState<'standard' | 'micro' | 'high'>('standard');

  const templates = [
    {
      id: 'python-fastapi',
      name: 'Python FastAPI',
      runtimeStr: 'Python 3.12 (FastAPI)',
      canonicalRuntime: 'python',
      defaultPort: 8000,
      desc: 'High-performance async microservice with automatic OpenAPI swagger docs and health probe',
      tag: 'FastAPI'
    },
    {
      id: 'react-vite',
      name: 'React + Vite',
      runtimeStr: 'Node.js 20 (Vite)',
      canonicalRuntime: 'react',
      defaultPort: 3000,
      desc: 'Client-side SPA with TypeScript, Tailwind CSS, and optimized production build',
      tag: 'Frontend'
    },
    {
      id: 'go-microservice',
      name: 'Go Microservice',
      runtimeStr: 'Go 1.22',
      canonicalRuntime: 'go',
      defaultPort: 8080,
      desc: 'Compiled lightweight binary with minimal memory footprint and fast boot time',
      tag: 'Compiled'
    },
    {
      id: 'node-service',
      name: 'Node.js API',
      runtimeStr: 'Node.js 20',
      canonicalRuntime: 'node',
      defaultPort: 3000,
      desc: 'Event-driven Node.js REST backend service with lightweight container profile',
      tag: 'Node'
    }
  ];

  const handleTemplateSelect = (t: typeof templates[0]) => {
    setRuntimeTemplate(t.id);
    setPort(t.defaultPort);
    if (name) {
      setRepoUrl(`https://github.com/${gitHubOwner}/${name}`);
    }
  };

  const handleNameChange = (val: string) => {
    const slugified = val.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    setName(slugified);
    setRepoUrl(`https://github.com/${gitHubOwner}/${slugified}`);
  };

  const PROVISIONING_STEPS: { id: ProvisioningJobStep; title: string; desc: string }[] = [
    {
      id: 'VALIDATE_CONFIGURATION',
      title: 'Validate configuration',
      desc: 'Verify application naming (RFC 1123), port ranges, and starter template dependencies'
    },
    {
      id: 'GENERATE_PROJECT',
      title: 'Generate project',
      desc: `Scaffold complete ${runtimeTemplate} source code, containerfile, and configuration`
    },
    {
      id: 'GENERATE_MANIFEST',
      title: 'Generate devforge.yaml',
      desc: 'Synthesize standard devforge.yaml manifest specifying services, ports, and limits'
    },
    {
      id: 'VALIDATE_PROJECT',
      title: 'Validate project',
      desc: 'Ensure generated files, runtime entrypoints, and manifest schemas are valid'
    },
    {
      id: 'CREATING_REPOSITORY',
      title: 'Create GitHub repository',
      desc: `Provision remote repository under GitHub owner (${gitHubOwner})`
    },
    {
      id: 'PUSHING_REPOSITORY',
      title: 'Push repository',
      desc: 'Initialize local git, commit initial scaffold, and push to main branch'
    },
    {
      id: 'COMPLETED',
      title: 'Ready',
      desc: 'Application provisioned, registered in PostgreSQL, and ready for deployment'
    }
  ];

  const STEP_ORDER: ProvisioningJobStep[] = [
    'VALIDATE_CONFIGURATION',
    'PREPARE_WORKSPACE',
    'GENERATE_PROJECT',
    'GENERATE_MANIFEST',
    'VALIDATE_PROJECT',
    'CREATING_REPOSITORY',
    'PUSHING_REPOSITORY',
    'COMPLETED'
  ];

  const getStepStatus = (stepKey: ProvisioningJobStep) => {
    if (!currentJob) return 'pending';
    if (currentJob.status === 'READY') return 'completed';

    // Normalize PREPARE_WORKSPACE
    let curStep = currentJob.current_step;
    if (curStep === 'PREPARE_WORKSPACE') {
      curStep = 'VALIDATE_CONFIGURATION';
    }

    const currentIdx = STEP_ORDER.indexOf(curStep);
    const targetIdx = STEP_ORDER.indexOf(stepKey);

    if (currentJob.status === 'FAILED') {
      if (targetIdx < currentIdx) return 'completed';
      if (targetIdx === currentIdx) return 'failed';
      return 'pending';
    }

    if (targetIdx < currentIdx) return 'completed';
    if (targetIdx === currentIdx) return 'active';
    return 'pending';
  };

  useEffect(() => {
    if (!activeJobId || stage !== 'provisioning') return;

    let isMounted = true;
    let timer: any = null;

    const poll = async () => {
      try {
        const job = await api.getProvisioningJob(activeJobId);
        if (!isMounted) return;
        setCurrentJob(job);

        if (job.status === 'READY') {
          try {
            const details = await api.getApplicationDetails(job.application_id);
            if (isMounted) {
              setProvisionResult({
                application: details.application,
                provisioning_status: 'READY',
                job_id: job.id,
                generated_path: details.application.generated_path,
                manifest: details.application.manifest_yaml,
                files_generated: [],
                message: `Application '${details.application.name}' provisioned successfully.`
              });
              setStage('ready');
            }
          } catch {
            if (isMounted) setStage('ready');
          }
          return;
        }

        if (job.status === 'FAILED') {
          if (isMounted) {
            setError(job.error_message || `Provisioning failed at step: ${job.current_step}`);
            setStage('failed');
          }
          return;
        }

        timer = setTimeout(poll, 750);
      } catch (err: any) {
        if (!isMounted) return;
        timer = setTimeout(poll, 1200);
      }
    };

    poll();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, [activeJobId, stage]);

  const handleRetryJob = async () => {
    if (!activeJobId) return;
    try {
      setError(null);
      setStage('provisioning');
      const retried = await api.retryProvisioningJob(activeJobId);
      setCurrentJob(retried);
    } catch (err: any) {
      setError(err.message || 'Failed to retry provisioning job.');
      setStage('failed');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Application name is required.');
      return;
    }
    setError(null);
    setStage('provisioning');
    setCurrentJob(null);

    try {
      const selectedTpl = templates.find((t) => t.id === runtimeTemplate);
      const result = await onCreateApp({
        name,
        description: description || `Self-serviced ${selectedTpl?.name} created via DevForge IDP.`,
        team,
        runtime: selectedTpl?.canonicalRuntime || 'python',
        template: runtimeTemplate,
        repository_url: repoUrl,
        branch,
        environment,
        database_type: databaseType,
        deployment_strategy: deploymentStrategy,
        version: 'v1.0.0',
        port: Number(port),
        replicas: Number(replicas)
      });

      if (result.provisioning_status === 'READY') {
        setProvisionResult(result);
        setStage('ready');
      } else if (result.job_id) {
        setActiveJobId(result.job_id);
      } else {
        setProvisionResult(result);
        setStage('ready');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to provision application.');
      setStage('failed');
    }
  };

  // 1. PROVISIONING PROGRESS SCREEN
  if (stage === 'provisioning') {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-6 animate-in fade-in duration-200">
        <div className="border border-zinc-800 bg-[#0e0e11] rounded-lg p-6 space-y-6 shadow-xl">
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
              <div>
                <h2 className="text-base font-semibold text-white font-mono">Provisioning Application: {name}</h2>
                <p className="text-xs text-zinc-400">PostgreSQL worker queue executing background provisioning pipeline</p>
              </div>
            </div>
            {currentJob && (
              <div className="text-right">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700">
                  Job #{currentJob.id}
                </span>
                {currentJob.attempt > 1 && (
                  <div className="text-[10px] text-amber-400 font-mono mt-1">
                    Attempt {currentJob.attempt} of {currentJob.max_attempts}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-4">
            {PROVISIONING_STEPS.map((s) => {
              const status = getStepStatus(s.id);
              const isCompleted = status === 'completed';
              const isCurrent = status === 'active';
              const isFailed = status === 'failed';

              return (
                <div key={s.id} className="flex items-start gap-3.5">
                  <div className="mt-0.5">
                    {isCompleted ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-emerald-400">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                    ) : isFailed ? (
                      <div className="w-5 h-5 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center text-red-400">
                        <XCircle className="w-3 h-3" />
                      </div>
                    ) : isCurrent ? (
                      <div className="w-5 h-5 rounded-full bg-zinc-800 border border-emerald-400 flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full border border-zinc-700 bg-zinc-900/50" />
                    )}
                  </div>
                  <div>
                    <div className={`text-xs font-semibold font-mono ${
                      isCompleted ? 'text-zinc-200' : isCurrent ? 'text-white font-bold' : isFailed ? 'text-red-400' : 'text-zinc-500'
                    }`}>
                      {s.title}
                    </div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">{s.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-4 border-t border-zinc-800/80 text-[11px] text-zinc-500 font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Isolated workspace: .devforge/generated/app_{currentJob?.application_id || '...'}</span>
            </div>
            <span className="text-[10px] text-zinc-500">PostgreSQL SKIP LOCKED Queue</span>
          </div>
        </div>
      </div>
    );
  }

  // 2. SUCCESS SCREEN: APPLICATION READY
  if (stage === 'ready' && provisionResult) {
    const app = provisionResult.application;
    return (
      <div className="p-8 max-w-3xl mx-auto space-y-6 animate-in fade-in duration-200">
        <div className="border border-emerald-500/40 bg-[#0e0e11] rounded-lg p-6 space-y-6 shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white font-mono">{app.name}</h2>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    READY
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-0.5">Application successfully generated and registered in PostgreSQL</p>
              </div>
            </div>
            <span className="text-xs font-mono text-zinc-500">ID #{app.id}</span>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-500 uppercase">Template</span>
              <div className="text-zinc-200 font-semibold mt-1">{app.template || runtimeTemplate}</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-500 uppercase">Runtime</span>
              <div className="text-zinc-200 font-semibold mt-1">{app.runtime}</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-500 uppercase">Environment</span>
              <div className="text-zinc-200 font-semibold mt-1 uppercase">{app.environment}</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-500 uppercase">Port / Database</span>
              <div className="text-zinc-200 font-semibold mt-1">:{app.port} / {app.database_type || 'none'}</div>
            </div>
          </div>

          {/* Generated Project Files Location */}
          <div className="p-3.5 bg-zinc-950 rounded border border-zinc-800 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-zinc-400">
              <div className="flex items-center gap-2">
                <FolderTree className="w-4 h-4 text-emerald-400" />
                <span className="text-zinc-200 font-semibold">Generated Project Location:</span>
              </div>
              <span className="text-[10px] text-zinc-500">{provisionResult.files_generated.length} files scaffolded</span>
            </div>
            <div className="text-emerald-400 bg-zinc-900/80 px-3 py-1.5 rounded border border-zinc-800 text-[11px]">
              {provisionResult.generated_path || `.devforge/generated/${app.name}`}
            </div>
          </div>

          {/* GitHub Repository */}
          <div className="p-3.5 bg-zinc-950 rounded border border-zinc-800 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-zinc-400">
              <div className="flex items-center gap-2">
                <Github className="w-4 h-4 text-emerald-400" />
                <span className="text-zinc-200 font-semibold">GitHub Repository</span>
              </div>
              <span className="text-[10px] text-zinc-500">
                Branch: {app.repository_default_branch || app.branch || 'main'}
              </span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded bg-zinc-900/80 border border-zinc-800">
              <div className="flex items-center gap-2">
                <GitBranch className="w-3.5 h-3.5 text-zinc-500" />
                <span className="text-xs text-emerald-400 font-semibold">
                  {app.repository_owner && app.repository_name
                    ? `${app.repository_owner}/${app.repository_name}`
                    : (app.repository_url || '').replace(/^https:\/\/github\.com\//, '')}
                </span>
              </div>
              {app.repository_url && (
                <a
                  href={app.repository_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/30 transition"
                >
                  <span>Open Repository</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>

          {/* devforge.yaml snippet */}
          {provisionResult.manifest && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <div className="flex items-center gap-1.5">
                  <FileCode className="w-3.5 h-3.5 text-zinc-400" />
                  <span className="font-mono text-zinc-300">Generated devforge.yaml</span>
                </div>
                <span className="text-[10px] font-mono text-zinc-500">apiVersion: devforge/v1</span>
              </div>
              <pre className="p-3 bg-zinc-950 rounded border border-zinc-800 text-[11px] font-mono text-zinc-300 overflow-x-auto max-h-48 leading-relaxed">
                {provisionResult.manifest}
              </pre>
            </div>
          )}

          {/* Actions */}
          <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
            <button
              onClick={onBack}
              className="px-3.5 py-2 rounded text-xs font-mono text-zinc-400 hover:text-white transition"
            >
              ← Back to Applications
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={() => onSuccess(app)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded font-mono transition flex items-center gap-1.5 shadow"
              >
                <span>Open Application</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 3. FAILURE SCREEN: PROVISIONING FAILED
  if (stage === 'failed') {
    return (
      <div className="p-8 max-w-xl mx-auto space-y-6 animate-in fade-in duration-200">
        <div className="border border-red-500/40 bg-[#0e0e11] rounded-lg p-6 space-y-6 shadow-2xl">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center text-red-400 shrink-0">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-mono">Provisioning Failed</h2>
              <p className="text-xs text-zinc-400 mt-1">
                The provisioning pipeline encountered an error. Existing platform records remain uncorrupted.
              </p>
              {currentJob && (
                <div className="flex items-center gap-2 mt-2 text-[11px] font-mono text-zinc-400">
                  <span>Failed at: <strong className="text-red-300">{currentJob.current_step}</strong></span>
                  <span>•</span>
                  <span>Attempt {currentJob.attempt} / {currentJob.max_attempts}</span>
                </div>
              )}
            </div>
          </div>

          <div className="p-3.5 bg-red-950/30 border border-red-900/60 rounded text-xs text-red-200 font-mono leading-relaxed break-words">
            {error || 'An unexpected error occurred during project generation.'}
          </div>

          <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
            <button
              onClick={onBack}
              className="px-3.5 py-2 text-xs font-mono text-zinc-400 hover:text-white transition"
            >
              Cancel
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setError(null);
                  setStage('wizard');
                }}
                className="px-3.5 py-2 rounded border border-zinc-700 hover:bg-zinc-800 text-zinc-300 text-xs font-mono transition"
              >
                Edit Settings
              </button>
              {currentJob?.is_retryable && (
                <button
                  onClick={handleRetryJob}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded font-mono transition flex items-center gap-1.5 shadow"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Retry Provisioning</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 4. WIZARD FORM (Steps 1, 2, 3)
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
            Self-service a real, runnable microservice scaffolded directly from DevForge starter templates.
          </p>
        </div>
      </div>

      {/* Progress Steps Indicator */}
      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
        {[
          { num: 1, title: 'Basics & Identity' },
          { num: 2, title: 'Runtime & Template' },
          { num: 3, title: 'Environment & Config' }
        ].map((s) => (
          <div
            key={s.num}
            onClick={() => setStep(s.num as any)}
            className={`p-3 rounded border cursor-pointer transition ${
              step === s.num
                ? 'border-emerald-500 bg-zinc-900/70 text-white font-semibold'
                : 'border-zinc-800 bg-zinc-950 text-zinc-500 hover:border-zinc-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${
                step === s.num ? 'bg-emerald-500 text-black font-bold' : 'bg-zinc-800 text-zinc-400'
              }`}>
                {s.num}
              </span>
              <span>{s.title}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Form (7 cols) + Live Manifest Preview (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form Container */}
        <div className="lg:col-span-7 border border-zinc-800 bg-[#0e0e11] rounded-md p-5">
          {error && (
            <div className="mb-4 p-3 rounded bg-red-950/50 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* STEP 1: Basics */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
                    <span>Application Name</span>
                    <span className="text-[10px] text-zinc-500 font-mono">RFC 1123 format (lowercase alphanumeric & hyphens)</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. order-processing-service"
                    value={name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Owning Team
                  </label>
                  <select
                    value={team}
                    onChange={(e) => setTeam(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                  >
                    <option value="Platform Engineering">Platform Engineering</option>
                    <option value="Core Banking & Payments">Core Banking & Payments</option>
                    <option value="Catalog & Inventory">Catalog & Inventory</option>
                    <option value="Security & Identity">Security & Identity</option>
                    <option value="Data & Analytics">Data & Analytics</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Brief architectural summary of this service..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    disabled={!name.trim()}
                    className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold rounded transition disabled:opacity-50"
                  >
                    Next: Runtime & Template →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Runtime & Starter Template */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-zinc-200">
                    Select Starter Template
                  </label>
                  <div className="grid grid-cols-1 gap-2.5">
                    {templates.map((tpl) => {
                      const isSelected = runtimeTemplate === tpl.id;
                      return (
                        <div
                          key={tpl.id}
                          onClick={() => handleTemplateSelect(tpl)}
                          className={`p-3 rounded border cursor-pointer transition ${
                            isSelected
                              ? 'border-emerald-500 bg-zinc-900 text-white'
                              : 'border-zinc-800 bg-zinc-950 text-zinc-300 hover:border-zinc-700'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-xs font-mono">{tpl.name}</span>
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 font-mono">
                                {tpl.tag}
                              </span>
                            </div>
                            <span className="text-[11px] font-mono text-zinc-400">Default port :{tpl.defaultPort}</span>
                          </div>
                          <p className="text-[11px] text-zinc-400 mt-1">{tpl.desc}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Repository URL
                  </label>
                  <input
                    type="text"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                  />
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
                    Next: Environment & Config →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Environment, Database & Sizing */}
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

                {/* Database Dependency */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Database Dependency</span>
                  </label>
                  <div className="grid grid-cols-4 gap-2 text-xs font-mono">
                    {[
                      { id: 'none', label: 'None' },
                      { id: 'postgresql', label: 'PostgreSQL' },
                      { id: 'mysql', label: 'MySQL' },
                      { id: 'redis', label: 'Redis' }
                    ].map((db) => (
                      <button
                        type="button"
                        key={db.id}
                        onClick={() => setDatabaseType(db.id)}
                        className={`p-2 rounded border text-center font-medium transition ${
                          databaseType === db.id
                            ? 'border-emerald-500 bg-zinc-900 text-white'
                            : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700'
                        }`}
                      >
                        {db.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Deployment Strategy */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Deployment Strategy
                  </label>
                  <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                    {[
                      { id: 'rolling', label: 'Rolling Update' },
                      { id: 'recreate', label: 'Recreate' },
                      { id: 'canary', label: 'Canary' }
                    ].map((st) => (
                      <button
                        type="button"
                        key={st.id}
                        onClick={() => setDeploymentStrategy(st.id)}
                        className={`p-2 rounded border text-center font-medium transition ${
                          deploymentStrategy === st.id
                            ? 'border-emerald-500 bg-zinc-900 text-white'
                            : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700'
                        }`}
                      >
                        {st.label}
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
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition shadow-sm flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Provision Application</span>
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
              <span className="text-[10px] font-mono text-zinc-500">apiVersion: devforge/v1</span>
            </div>

            <pre className="mt-3 text-[11px] font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800 overflow-x-auto leading-relaxed">
{`apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: "${name || 'example-service'}"
  version: "1.0.0"
  description: "${description || 'Self-serviced application'}"
  team: "${team}"
spec:
  runtime: "${templates.find((t) => t.id === runtimeTemplate)?.canonicalRuntime || 'python'}"
  template: "${runtimeTemplate}"
  environment: "${environment}"
  port: ${port}
  database:
    type: "${databaseType}"
  build:
    docker: true
    dockerfile: "Dockerfile"
  deployment:
    strategy: "${deploymentStrategy}"
    replicas: ${replicas}
  healthCheck:
    path: "${runtimeTemplate === 'go-microservice' ? '/health' : runtimeTemplate === 'react-vite' ? '/' : '/healthz'}"
    port: ${port}`}
            </pre>
          </div>

          <div className="mt-4 p-3 rounded bg-zinc-900/60 border border-zinc-800 text-[11px] text-zinc-400 font-mono space-y-1">
            <div className="text-zinc-300 font-semibold flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span>Phase 2 Provisioning Pipeline:</span>
            </div>
            <div>• Real template discovery from templates/{runtimeTemplate}</div>
            <div>• Scaffolds real project in .devforge/generated/{name || 'app'}</div>
            <div>• Validates devforge.yaml v1 schema</div>
            <div>• Persists record in PostgreSQL with READY status</div>
          </div>
        </div>
      </div>
    </div>
  );
};
