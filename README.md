# DevForge — Internal Developer Platform (IDP)

> **Phase 1: Platform Foundation & Core Developer Workflows**

DevForge is an **Internal Developer Platform (IDP)** built to empower software engineers to self-service common DevOps workflows: creating applications, managing environments, triggering deployments, observing service health, and tracking team activity.

DevForge's interface is intentionally designed like serious engineering infrastructure tools (e.g. Datadog, HashiCorp, AWS, Linear, and Vercel) — emphasizing high information density, clean typography, state-first color indicators, and zero decorative fluff.

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0
- **Database**: PostgreSQL 16 (with automatic zero-friction SQLite fallback for local standalone mode)
- **Local Infrastructure**: Docker & Docker Compose
- **Source Control & CI**: Git, GitHub Actions workflows for tests and container checks

---

## 📁 Repository Structure

```
DevForge/
├── frontend/                     # React + TypeScript + Tailwind UI
│   ├── src/
│   │   ├── components/           # Layout, navigation, tables, modals, badges
│   │   ├── pages/                # Overview, Applications, CreateApp, etc.
│   │   ├── services/             # Typed API client
│   │   └── types/                # Domain models & state definitions
│   ├── index.html
│   ├── vite.config.ts
│   └── tailwind.config.js
├── backend/                      # Python FastAPI API server
│   ├── app/
│   │   ├── api/                  # API routers (overview, apps, deployments, etc.)
│   │   ├── core/                 # Configuration & settings
│   │   ├── db/                   # Session & realistic seed data
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic validation schemas
│   │   └── main.py               # Application entrypoint & CORS
│   └── requirements.txt
├── templates/                    # Starter templates for self-serviced apps
│   ├── python-fastapi/
│   ├── react-vite/
│   ├── go-microservice/
│   └── node-service/
├── docker/                       # Container definitions & Nginx configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── .github/                      # GitHub Actions workflows & PR template
│   └── workflows/
├── docker-compose.yml            # Multi-container orchestration
├── .env.example                  # Environment configuration
└── README.md
```

---

## 🚀 Getting Started

### Option 1: Running with Docker Compose (Recommended)

To run the complete stack (PostgreSQL + FastAPI backend + React frontend):

```bash
# 1. Clone or navigate to the repository
cd DevForge

# 2. Copy the environment configuration
cp .env.example .env

# 3. Spin up all services
docker compose up --build -d

# 4. Access the applications
# Frontend Dashboard: http://localhost:3000
# Backend API Docs:   http://localhost:8000/docs
# Health Probe:       http://localhost:8000/health
```

### Option 2: Running Locally for Fast Development

#### 1. Start the Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*Note: If no PostgreSQL instance is detected, DevForge automatically initializes a local SQLite database seeded with realistic platform data.*

#### 2. Start the Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🖥️ Platform Navigation & Features

| View | Purpose |
|------|---------|
| **Overview** | High-signal dashboard: 4 key metrics, Recent Deployments, Service Health table, and live Recent Activity feed. |
| **Applications** | Filterable inventory of microservices & web apps with runtime, repository, environment, and last deployment status. Includes application detail slide-over. |
| **Create Application** | Streamlined 3-step self-service wizard: Metadata -> Starter Template / Git URL -> Sizing & Target Environment with live manifest preview. |
| **Environments** | Status and topology of Production, Staging, Development, and Preview clusters. |
| **Deployments** | Full audit log of deployment runs, build stage breakdown (Lint, Build, Test, Deploy), and container build logs. |
| **Infrastructure** | Connected compute nodes, managed databases, Redis clusters, and network ingress status. |
| **Monitoring** | Telemetry overview: P95 latency, requests/second, error rates, and CPU/memory utilization. |
| **Activity** | Chronological audit log of developer events and infrastructure mutations. |
| **Settings** | Workspace configuration, Git provider webhooks, and container registry settings. |
