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
  Github,
  Layers,
  Code2,
  Box,
  Eye,
  Sliders
} from 'lucide-react';
import { api } from '../services/api';
import { Application, ApplicationProvisioningResponse, ProvisioningJob, ProvisioningJobStep, ApplicationTemplate, TemplatePreviewResponse } from '../types';
import { SEED_TEMPLATES } from '../services/seedData';

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
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [currentJob, setCurrentJob] = useState<ProvisioningJob | null>(null);
  const [provisionResult, setProvisionResult] = useState<ApplicationProvisioningResponse | null>(null);

  // Template Catalog State
  const [templates, setTemplates] = useState<ApplicationTemplate[]>(SEED_TEMPLATES);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('python-fastapi');
  const [previewTab, setPreviewTab] = useState<'preview' | 'manifest'>('preview');
  const [serverPreview, setServerPreview] = useState<TemplatePreviewResponse | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [team, setTeam] = useState('Platform Engineering');
  const [description, setDescription] = useState('');
  const [gitHubOwner, setGitHubOwner] = useState('sripriyancsbs');
  const [repoVisibility, setRepoVisibility] = useState<'private' | 'public'>('private');
  const [repoUrl, setRepoUrl] = useState(`https://github.com/sripriyancsbs/`);
  const [branch, setBranch] = useState('main');

  // Environment & Sizing
  const [environment, setEnvironment] = useState('development');
  const [port, setPort] = useState(8000);
  const [replicas, setReplicas] = useState(2);
  const [databaseType, setDatabaseType] = useState('none');
  const [deploymentStrategy, setDeploymentStrategy] = useState('rolling');
  const [envVarsText, setEnvVarsText] = useState('');

  // Fetch templates and GitHub status on mount
  useEffect(() => {
    api.getGitHubStatus()
      .then((res) => {
        if (res && res.owner) setGitHubOwner(res.owner);
      })
      .catch(() => {});

    api.getTemplates()
      .then((tpls) => {
        if (tpls && tpls.length > 0) {
          setTemplates(tpls);
          const first = tpls[0];
          setSelectedTemplateId(first.template_id);
          setPort(first.default_values?.port || 8000);
        }
      })
      .catch(() => {
        setTemplates(SEED_TEMPLATES);
      });
  }, []);

  const selectedTemplate = templates.find((t) => t.template_id === selectedTemplateId) || templates[0] || SEED_TEMPLATES[0];

  const handleTemplateSelect = (tpl: ApplicationTemplate) => {
    setSelectedTemplateId(tpl.template_id);
    const defaultPort = tpl.default_values?.port || (tpl.runtime === 'go' ? 8080 : tpl.runtime === 'node' ? 3000 : 8000);
    setPort(defaultPort);
    if (name) {
      setRepoUrl(`https://github.com/${gitHubOwner}/${name}`);
    }
  };

  const handleNameChange = (val: string) => {
    const sanitized = val.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    setName(sanitized);
    setRepoUrl(`https://github.com/${gitHubOwner}/${sanitized}`);
    validateName(sanitized);
  };

  const validateName = (val: string): boolean => {
    const errs: string[] = [];
    if (!val.trim()) {
      errs.push('Application name is required.');
    } else {
      if (val.length < 2 || val.length > 63) {
        errs.push('Application name must be between 2 and 63 characters.');
      }
      const rfc1123Regex = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?$/;
      if (!rfc1123Regex.test(val)) {
        errs.push('Name must follow RFC 1123: lowercase letters, numbers, and hyphens only, and cannot start or end with a hyphen.');
      }
      if (val.includes('..') || val.includes('/') || val.includes('\\')) {
        errs.push('Name contains forbidden path traversal characters.');
      }
    }
    setValidationErrors(errs);
    return errs.length === 0;
  };

  // Live Template Preview Loader
  useEffect(() => {
    if (!selectedTemplate) return;
    const appName = name.trim() || 'example-app';
    api.previewTemplate(selectedTemplate.template_id, {
      application_name: appName,
      environment,
      variables: {
        port,
        replicas,
        database_type: databaseType
      }
    })
      .then(res => setServerPreview(res))
      .catch(() => setServerPreview(null));
  }, [selectedTemplateId, name, environment, port, replicas, databaseType]);

  const PROVISIONING_STEPS: { id: ProvisioningJobStep; title: string; desc: string }[] = [
    {
      id: 'VALIDATE_CONFIGURATION',
      title: 'Validate configuration',
      desc: 'Verify application naming (RFC 1123), port ranges, and starter template dependencies'
    },
    {
      id: 'GENERATE_PROJECT',
      title: 'Generate project',
      desc: `Scaffold complete ${selectedTemplate?.name || 'starter'} source code, containerfile, and configuration`
    },
    {
      id: 'GENERATE_MANIFEST',
      title: 'Generate devforge.yaml',
      desc: 'Synthesize standard devforge.yaml manifest specifying services, ports, and limits'
    },
    {
      id: 'GENERATING_CI_WORKFLOW',
      title: 'Generate CI workflow',
      desc: 'Synthesize automated GitHub Actions CI workflow (.github/workflows/ci.yml)'
    },
    {
      id: 'VALIDATE_PROJECT',
      title: 'Validate project',
      desc: 'Ensure generated files, runtime entrypoints, syntax, and zero unresolved variables'
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
    'GENERATING_CI_WORKFLOW',
    'VALIDATE_PROJECT',
    'CREATING_REPOSITORY',
    'PUSHING_REPOSITORY',
    'COMPLETED'
  ];

  const getStepStatus = (stepKey: ProvisioningJobStep) => {
    if (!currentJob) return 'pending';
    if (currentJob.status === 'READY') return 'completed';

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

    if (!validateName(name)) {
      setError('Please resolve all validation errors before proceeding.');
      return;
    }

    if (port < 1 || port > 65535) {
      setError('Port must be between 1 and 65535.');
      return;
    }

    setError(null);
    setStage('provisioning');
    setCurrentJob(null);

    // Parse env vars
    const envVarsObj: Record<string, string> = {};
    if (envVarsText.trim()) {
      envVarsText.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
          const [k, ...v] = trimmed.split('=');
          envVarsObj[k.trim()] = v.join('=').trim();
        }
      });
    }

    try {
      const result = await onCreateApp({
        name,
        description: description || `Self-serviced ${selectedTemplate.name} created via DevForge IDP.`,
        team,
        runtime: selectedTemplate.runtime,
        template: selectedTemplate.template_id,
        template_id: selectedTemplate.template_id,
        template_version: selectedTemplate.version,
        repository_url: repoUrl,
        repository_visibility: repoVisibility,
        branch,
        environment,
        database_type: databaseType,
        deployment_strategy: deploymentStrategy,
        version: 'v1.0.0',
        port: Number(port),
        replicas: Number(replicas),
        env_vars: envVarsObj
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
      <div className="p-4 sm:p-8 max-w-2xl mx-auto space-y-6 w-full min-w-0 animate-in fade-in duration-200">
        <div className="border border-zinc-800 bg-[#0e0e11] rounded-lg p-6 space-y-6 shadow-xl">
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
              <div>
                <h2 className="text-base font-semibold text-white font-mono">Provisioning Application: {name}</h2>
                <p className="text-xs text-zinc-400">Template-driven provisioning pipeline scaffolding {selectedTemplate.name} v{selectedTemplate.version}</p>
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
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </div>
                    ) : isCurrent ? (
                      <div className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      </div>
                    ) : isFailed ? (
                      <div className="w-5 h-5 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center">
                        <XCircle className="w-3.5 h-3.5" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-500 flex items-center justify-center text-[10px] font-mono">
                        •
                      </div>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono font-medium ${isCurrent ? 'text-white' : isCompleted ? 'text-zinc-200' : isFailed ? 'text-red-400' : 'text-zinc-500'}`}>
                        {s.title}
                      </span>
                      {isCurrent && (
                        <span className="text-[10px] px-1.5 py-0.2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded font-mono animate-pulse">
                          running
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-500 mt-0.5">{s.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // 2. READY SCREEN: PROVISIONING SUCCESSFUL
  if (stage === 'ready' && provisionResult) {
    const app = provisionResult.application;
    return (
      <div className="p-4 sm:p-8 max-w-2xl mx-auto space-y-6 w-full min-w-0 animate-in fade-in duration-200">
        <div className="border border-emerald-500/40 bg-[#0e0e11] rounded-lg p-6 space-y-6 shadow-2xl">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-emerald-400 shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-mono">Application Provisioned Successfully</h2>
              <p className="text-xs text-zinc-400 mt-1">
                Scaffolded with <span className="text-emerald-400 font-semibold">{selectedTemplate.name} v{selectedTemplate.version}</span>. Initialized in PostgreSQL and ready for deployment.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <div className="text-zinc-500 text-[10px]">APPLICATION</div>
              <div className="text-white font-semibold mt-0.5">{app.name}</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <div className="text-zinc-500 text-[10px]">TEMPLATE & VERSION</div>
              <div className="text-white font-semibold mt-0.5">{selectedTemplate.name} (v{selectedTemplate.version})</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <div className="text-zinc-500 text-[10px]">ENVIRONMENT</div>
              <div className="text-white font-semibold mt-0.5 uppercase">{app.environment}</div>
            </div>
            <div className="p-3 bg-zinc-950 rounded border border-zinc-800">
              <div className="text-zinc-500 text-[10px]">CONTAINER PORT</div>
              <div className="text-white font-semibold mt-0.5">{app.port}</div>
            </div>
          </div>

          <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
            <button
              onClick={onBack}
              className="px-3.5 py-2 rounded text-xs font-mono text-zinc-400 hover:text-white transition"
            >
              ← Back to Applications
            </button>
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
    );
  }

  // 3. FAILURE SCREEN: PROVISIONING FAILED
  if (stage === 'failed') {
    return (
      <div className="p-4 sm:p-8 max-w-xl mx-auto space-y-6 w-full min-w-0 animate-in fade-in duration-200">
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
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6 w-full min-w-0" data-testid="create-application-page">
      {/* Header */}
      <div className="flex items-center gap-3 pb-2 border-b border-zinc-800/80">
        <button
          onClick={onBack}
          aria-label="Back to Applications"
          className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Create Application
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Select a reusable template to generate, validate, and scaffold a production-ready application.
          </p>
        </div>
      </div>

      {/* Progress Steps Indicator */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
        {[
          { num: 1, title: 'Identity & Source' },
          { num: 2, title: 'Template Catalog' },
          { num: 3, title: 'Runtime & Preview' }
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

      {/* Main Grid: Form (7 cols) + Live Template & Manifest Preview (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-w-0">
        {/* Form Container */}
        <div className="lg:col-span-7 border border-zinc-800 bg-[#0e0e11] rounded-md p-5 min-w-0">
          {error && (
            <div className="mb-4 p-3 rounded bg-red-950/50 border border-red-800/80 text-red-200 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {validationErrors.length > 0 && (
            <div className="mb-4 p-3 rounded bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs space-y-1">
              {validationErrors.map((err, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  <span>{err}</span>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* STEP 1: Basics & Identity */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
                    <span>Application Name</span>
                    <span className="text-[10px] text-zinc-500 font-mono">RFC 1123 compliant</span>
                  </label>
                  <input
                    type="text"
                    required
                    id="app-name-input"
                    data-testid="input-app-name"
                    placeholder="e.g. order-processing-service"
                    value={name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                  />
                  <p className="text-[10px] text-zinc-500">Must contain only lowercase alphanumeric characters or '-', length 2-63.</p>
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
                    rows={2}
                    id="app-desc-input"
                    data-testid="app-desc-input"
                    placeholder="Brief architectural summary of this service..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
                      Repository Visibility
                    </label>
                    <select
                      value={repoVisibility}
                      onChange={(e) => setRepoVisibility(e.target.value as any)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 focus:outline-none focus:border-zinc-600 font-mono"
                    >
                      <option value="private">Private (Default)</option>
                      <option value="public">Public</option>
                    </select>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    id="btn-next-step-2"
                    data-testid="btn-next-step-2"
                    onClick={() => {
                      if (validateName(name)) {
                        setStep(2);
                      }
                    }}
                    disabled={!name.trim() || validationErrors.length > 0}
                    className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold rounded transition disabled:opacity-50"
                  >
                    Next: Select Template →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Template Catalog Selection */}
            {step === 2 && (
              <div className="space-y-4" data-testid="template-catalog-section">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Application Template Catalog</span>
                  </label>
                  <span className="text-[10px] text-zinc-400 font-mono">{templates.length} templates available</span>
                </div>

                {/* Compact Template Cards / Rows */}
                <div className="space-y-2.5">
                  {templates.map((tpl) => {
                    const isSelected = selectedTemplateId === tpl.template_id;
                    return (
                      <div
                        key={tpl.template_id}
                        data-testid={`template-card-${tpl.template_id}`}
                        onClick={() => handleTemplateSelect(tpl)}
                        className={`p-3 rounded-md border cursor-pointer transition ${
                          isSelected
                            ? 'border-emerald-500 bg-zinc-900/90 text-white shadow-sm'
                            : 'border-zinc-800 bg-zinc-950 text-zinc-300 hover:border-zinc-700'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs font-mono">{tpl.name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-mono">
                              v{tpl.version}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-mono">
                              {tpl.framework}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-zinc-400 whitespace-nowrap">
                            {tpl.runtime}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 mt-1.5 leading-relaxed">{tpl.description}</p>
                        
                        <div className="mt-2 pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500">
                          <span>Env: {tpl.supported_environments.join(', ')}</span>
                          <span>Port: :{tpl.default_values?.port || 8000}</span>
                        </div>
                      </div>
                    );
                  })}
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
                    id="btn-next-step-3"
                    data-testid="btn-next-step-3"
                    onClick={() => setStep(3)}
                    className="px-4 py-2 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold rounded transition"
                  >
                    Next: Runtime & Preview →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Environment, Database, Port & Submission */}
            {step === 3 && (
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200">
                    Target Environment
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
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

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-zinc-200">
                      Container Port
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={65535}
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

                {/* Optional Environment Variables */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
                    <span>Environment Variables (Optional)</span>
                    <span className="text-[10px] text-zinc-500 font-mono">KEY=VALUE per line</span>
                  </label>
                  <textarea
                    rows={2}
                    placeholder="LOG_LEVEL=info&#10;ENABLE_METRICS=true"
                    value={envVarsText}
                    onChange={(e) => setEnvVarsText(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-200 font-mono focus:outline-none focus:border-zinc-600"
                  />
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
                    id="btn-provision-submit"
                    data-testid="create-app-submit"
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

        {/* Live Template & Manifest Preview (5 cols) */}
        <div className="lg:col-span-5 border border-zinc-800 bg-[#0e0e11] rounded-md p-4 flex flex-col justify-between min-w-0">
          <div>
            {/* Preview Navigation Tabs */}
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPreviewTab('preview')}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono transition ${
                    previewTab === 'preview'
                      ? 'bg-zinc-800 text-white font-semibold'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Template Preview</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab('manifest')}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-mono transition ${
                    previewTab === 'manifest'
                      ? 'bg-zinc-800 text-white font-semibold'
                      : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5 text-blue-400" />
                  <span>devforge.yaml</span>
                </button>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">v{selectedTemplate.version}</span>
            </div>

            {/* TAB 1: Template Preview */}
            {previewTab === 'preview' && (
              <div className="mt-3 space-y-3 font-mono text-xs text-zinc-300" data-testid="template-preview-pane">
                <div className="p-3 bg-zinc-950 rounded border border-zinc-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500 text-[10px]">SELECTED TEMPLATE</span>
                    <span className="text-emerald-400 text-[10px] font-bold">ACTIVE</span>
                  </div>
                  <div className="text-white font-semibold">{selectedTemplate.name}</div>
                  <div className="text-[11px] text-zinc-400">
                    {selectedTemplate.runtime} • {selectedTemplate.framework} (v{selectedTemplate.version})
                  </div>
                </div>

                <div className="p-3 bg-zinc-950 rounded border border-zinc-800 space-y-1.5">
                  <div className="text-zinc-500 text-[10px]">APPLICATION TARGET</div>
                  <div className="text-white font-medium">{name || 'example-app'} ({environment})</div>
                  <div className="text-[11px] text-zinc-400">Container Port: {port} • DB: {databaseType}</div>
                </div>

                <div className="p-3 bg-zinc-950 rounded border border-zinc-800 space-y-1.5">
                  <div className="text-zinc-500 text-[10px]">KEY GENERATED COMPONENTS</div>
                  <ul className="space-y-1 text-[11px] text-zinc-400">
                    {(serverPreview?.key_generated_components || [
                      'Main entrypoint and routing configuration',
                      'Standard health probe endpoints (/healthz, /ready)',
                      'Container build specification (Dockerfile, .dockerignore)',
                      'Automated CI/CD workflow (.github/workflows/ci.yml)',
                      'Kubernetes deployment and service manifests'
                    ]).map((comp, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-emerald-500">•</span>
                        <span>{comp}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-3 bg-zinc-950 rounded border border-zinc-800 space-y-1.5">
                  <div className="text-zinc-500 text-[10px] flex items-center justify-between">
                    <span>GENERATED PROJECT STRUCTURE</span>
                    <span>{selectedTemplate.generated_project_structure.length} files</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 space-y-0.5 max-h-32 overflow-y-auto">
                    {selectedTemplate.generated_project_structure.map((file, idx) => (
                      <div key={idx} className="flex items-center gap-1.5">
                        <FolderTree className="w-3 h-3 text-zinc-500 shrink-0" />
                        <span>{file}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: devforge.yaml Manifest */}
            {previewTab === 'manifest' && (
              <pre className="mt-3 text-[11px] font-mono text-zinc-300 bg-zinc-950 p-3 rounded border border-zinc-800 overflow-x-auto leading-relaxed">
{`apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: "${name || 'example-service'}"
  version: "1.0.0"
  description: "${description || 'Self-serviced application'}"
  team: "${team}"
spec:
  template_id: "${selectedTemplate.template_id}"
  template_version: "${selectedTemplate.version}"
  runtime: "${selectedTemplate.runtime}"
  framework: "${selectedTemplate.framework}"
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
    path: "${selectedTemplate.runtime === 'go' ? '/health' : '/healthz'}"
    port: ${port}`}
              </pre>
            )}
          </div>

          <div className="mt-4 p-3 rounded bg-zinc-900/60 border border-zinc-800 text-[11px] text-zinc-400 font-mono space-y-1">
            <div className="text-zinc-300 font-semibold flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span>Phase 13 Scaffolding Engine:</span>
            </div>
            <div>• Discovered from templates/{selectedTemplate.template_id}</div>
            <div>• Deterministic token substitution with unresolved token detection</div>
            <div>• Full validation of entrypoints, dependencies, tests, & manifests</div>
            <div>• Persisted in PostgreSQL with template version association</div>
          </div>
        </div>
      </div>
    </div>
  );
};
