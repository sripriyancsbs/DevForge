# DevForge Infrastructure as Code (Terraform)

This directory contains declarative Infrastructure as Code (IaC) configurations for provisioning and managing DevForge Kubernetes environments and baseline services.

## Architecture

DevForge integrates Terraform to manage the underlying environment and platform resources, while keeping application provisioning, container image synchronization, and runtime rollout lifecycle managed by DevForge's specialized services.

```text
Developer / Platform Admin
             ↓
        DevForge IDP
             ↓
     Terraform Service
             ↓
     Kubernetes Provider
             ↓
     Kubernetes Cluster (devforge namespace, baseline config)
             ↓
DevForge Application Runtime (Deployments, Pods, Probes, Services)
```

## Directory Structure

```text
terraform/
├── modules/
│   ├── kubernetes/      # Baseline environment resources (namespace, env config)
│   └── application/     # Baseline application infrastructure config
├── environments/
│   └── development/     # Development environment composition
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
└── README.md
```

## Resource Ownership Model

To prevent competing controllers or state oscillation:

| Resource | Managed By | Purpose |
|---|---|---|
| **Namespace `devforge`** | Terraform | Environment boundary and resource isolation |
| **Environment ConfigMap** | Terraform | Global environment parameters and metadata |
| **Baseline Application Config** | Terraform | Version-controlled infrastructure defaults |
| **Application Deployment** | DevForge K8s Service | Real-time rollout, active container image updates, ready replicas |
| **NodePort / Service Routes** | DevForge K8s Service | Active service ingress, port mapping, and reachability |

## State Management & Security

* **Local State**: State files (`*.tfstate`, `*.tfstate.*`) are strictly excluded from version control via `.gitignore`.
* **No Secrets in State**: Secrets and credentials are not hardcoded or persisted inside Terraform manifests.
* **Idempotency**: Executing `terraform plan` and `terraform apply` converges declaratively to the desired state without destroying runtime objects.

## Usage

### 1. Initialize
```bash
cd environments/development
terraform init
```

### 2. Validate
```bash
terraform validate
```

### 3. Plan
```bash
terraform plan -out=tfplan
```

### 4. Apply
```bash
terraform apply tfplan
```
