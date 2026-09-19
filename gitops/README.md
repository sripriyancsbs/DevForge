# DevForge GitOps Repository

This repository represents the **declarative desired state** for Kubernetes applications orchestrated by the DevForge Internal Developer Platform (IDP) and continuously reconciled by **Argo CD**.

## Architecture & Principles

```
Developer
    ↓
DevForge IDP
    ↓
Application Repository (Source code, Dockerfile, CI workflow)
    ↓
GitHub Actions
    ↓
Docker Image (GHCR)
    ↓
GitOps Manifest Repository (This Repository)
    ↓
Argo CD
    ↓
Kubernetes (Local kind-devforge / Cluster)
    ↓
Prometheus + Grafana
```

1. **Git as the Single Source of Truth**: All Kubernetes manifests (Deployments, Services, ConfigMaps) are version-controlled here. No manual `kubectl apply` commands should be run against production/staging.
2. **Kustomize Topology**: Every application defines a reusable `base/` directory and environment-specific `overlays/` (e.g. `overlays/development/`).
3. **Immutable Image Tags**: Manifests reference deterministic image tags published to GitHub Container Registry (`ghcr.io/sripriyancsbs/<app-name>:<sha>`).
4. **Continuous Reconciliation & Drift Detection**: Argo CD monitors this Git repository, compares desired manifests with live cluster state, flags drift (`OUT_OF_SYNC`), and reconciles the workload to `SYNCED`.

## Directory Structure

```
gitops/
├── README.md
└── applications/
    └── <application-name>/
        ├── base/
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   └── kustomization.yaml
        └── overlays/
            └── development/
                ├── kustomization.yaml
                └── patch.yaml
```
