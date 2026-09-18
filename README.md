# DevForge — Internal Developer Platform (IDP)

> **Phase 1, Phase 2, & Phase 3 Complete: Core Platform Foundation, Application Provisioning Engine, and GitHub Integration**

DevForge is an **Internal Developer Platform (IDP)** built to empower software engineers to self-service common DevOps workflows: creating real runnable microservices, provisioning cloud Git repositories on GitHub, managing environments, triggering deployments, observing service telemetry, and auditing team activity.

DevForge's interface is intentionally designed like serious engineering infrastructure tools (e.g. Datadog, HashiCorp, AWS, Linear, and Vercel) — emphasizing high information density, clean typography, state-first color indicators, and zero decorative fluff.

---

## 🚀 DevForge Architecture & Phase 3 GitHub Integration

Phase 3 extends DevForge from local file generation to a real GitHub-connected platform.

### Distinguishing DevForge Platform vs. Application Repositories
- **DevForge Platform Repository**: `https://github.com/sripriyancsbs/DevForge` (the source repository for DevForge itself).
- **Application Repositories**: DevForge provisions a **separate, private GitHub repository** for each user-created application under `https://github.com/sripriyancsbs/<app-name>`.

### Complete Provisioning Workflow
```
Developer Wizard Submission (UI / API)
                  ↓
FastAPI Provisioning API (Registers job in PostgreSQL, returns 201 immediately)
                  ↓
Provisioning Worker (Acquires job with SELECT FOR UPDATE SKIP LOCKED)
                  ↓
1. VALIDATE_CONFIGURATION  (RFC 1123 name, template validation, runtime check)
                  ↓
2. PREPARE_WORKSPACE       (Isolated sandbox at .devforge/generated/app_<id>/)
                  ↓
3. GENERATE_PROJECT        (Scaffolds complete source files from starter template)
                  ↓
4. GENERATE_MANIFEST       (Synthesizes standardized devforge.yaml)
                  ↓
5. VALIDATE_PROJECT        (Validates generated entrypoints, containers, & manifest)
                  ↓
6. CREATING_REPOSITORY     (Calls GitHub API to create private repository sripriyancsbs/<app>)
                  ↓
7. PUSHING_REPOSITORY      (git init, git add ., git commit, git push to main)
                  ↓
8. READY                   (Stores repository metadata in PostgreSQL, logs Activity)
```

---

## 🏛️ Modular Repository Service Architecture

GitHub-specific operations are kept modular and decoupled from the worker core:

```
Provisioning Worker
        ↓
RepositoryService (High-level orchestration: repo creation, git init, push)
        ↓
GitHubProvider (Implements BaseRepositoryProvider interface)
        ↓
GitHubClient (HTTP client for GitHub REST API v3 with automatic credential scrubbing)
```

This abstraction allows future source control providers (such as GitLab or Bitbucket) to be added without modifying the provisioning worker state machine.

---

## 🔐 Git Credential Security & Defense-in-Depth

DevForge enforces strict credential handling across all layers:
1. **Never Stored in PostgreSQL**: The `applications` and `provisioning_jobs` tables contain only public repository metadata (`repository_url`, `repository_owner`, `repository_name`, `repository_default_branch`). Plaintext tokens are never persisted in the database.
2. **Never Exposed in API Responses**: `GET /api/v1/integrations/github/status` returns only `{ "connected": true, "owner": "sripriyancsbs" }` and sanitized status messages.
3. **Never Saved to Disk**: Local `.git/config` files on disk are configured strictly with clean URLs (`https://github.com/sripriyancsbs/<app>.git`). Credentials are passed solely as ephemeral memory arguments during `git push`.
4. **Stream Redaction**: All stdout and stderr streams from Git CLI commands and HTTP client errors are passed through `scrub_credentials()` regex redaction before logging or storing error messages.
5. **Worker Isolation**: The GitHub token is provided only to backend/worker containers through environment variables. The frontend never receives or handles the token.

---

## 📦 Supported Starter Templates

| Template ID | Name | Runtime | Default Port | Key Files Included |
|---|---|---|---|---|
| `python-fastapi` | Python FastAPI | `python` (Python 3.12) | 8000 | `main.py`, `requirements.txt`, `Dockerfile`, `devforge.yaml` |
| `react-vite` | React + Vite | `react` (Node.js 20) | 3000 | `package.json`, `index.html`, `vite.config.ts`, `src/App.tsx`, `Dockerfile`, `devforge.yaml` |
| `go-microservice` | Go Microservice | `go` (Go 1.22) | 8080 | `main.go`, `go.mod`, `Dockerfile`, `devforge.yaml` |
| `node-service` | Node.js API | `node` (Node.js 20) | 3000 | `server.js`, `package.json`, `Dockerfile`, `devforge.yaml` |

---

## 📜 `devforge.yaml` Specification

Every provisioned project contains a standardized `devforge.yaml` manifest that serves as the declarative source of truth:

```yaml
apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: customer-checkout-api
  version: v1.0.0
  description: Production checkout processing API provisioned via DevForge IDP
  team: Platform Engineering
spec:
  runtime: python
  template: python-fastapi
  environment: production
  port: 8000
  database:
    type: postgresql
  build:
    docker: true
    dockerfile: Dockerfile
  deployment:
    strategy: rolling
    replicas: 2
  healthCheck:
    path: /healthz
    port: 8000
```

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, PyYAML, Git CLI, HTTPX
- **Database**: PostgreSQL 16 (Strict PostgreSQL required; no SQLite fallback)
- **Queue/Worker**: PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` background polling worker
- **Source Control**: Git CLI, GitHub REST API v3
- **Containers**: Docker & Docker Compose

---

## 🚀 Getting Started

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```

Key environment variables:
```env
# GitHub Integration
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=sripriyancsbs

# PostgreSQL
POSTGRES_USER=devforge
POSTGRES_PASSWORD=devforge_secure_password
POSTGRES_DB=devforge_db
DATABASE_URL=postgresql://devforge:devforge_secure_password@postgres:5432/devforge_db
```

### GitHub Token Requirements
Create a GitHub Personal Access Token (classic or fine-grained) with:
- `repo` (Full control of private repositories: repo creation, commits, pushing)
- `read:user` (User profile verification)

### 2. Run with Docker Compose
```bash
docker compose up --build -d
```

### 3. Verify Services
- **Frontend Dashboard**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Status**: http://localhost:8000/api/v1/integrations/github/status

---

## 🧪 Running Automated Tests

```bash
# Run all backend unit & integration tests
docker compose exec backend pytest tests/ -v

# Run specific test suites:
docker compose exec backend pytest tests/test_github_service.py -v
docker compose exec backend pytest tests/test_provisioning_worker.py -v
docker compose exec backend pytest tests/test_api.py -v
```

---

## 🔧 Troubleshooting

| Issue | Cause | Resolution |
|---|---|---|
| `GitHub authentication failed` (401) | `GITHUB_TOKEN` is expired, invalid, or malformed. | Generate a fresh token on GitHub and update `.env`. |
| `GitHub permission denied` (403) | `GITHUB_TOKEN` lacks the `repo` scope. | Ensure the token has `repo` permissions to create private repositories. |
| `Repository 'owner/app' already exists` (409) | Target repository exists on GitHub. | Choose a unique application name or delete the remote repository before provisioning. |
| `git binary not found` (127) | `git` is not installed on the system PATH. | Ensure Git is installed in the container image (`apt-get install -y git`). |
| `GitHub API connection timed out` | Outbound network connectivity issue. | Verify internet access and firewall settings for `api.github.com`. |
