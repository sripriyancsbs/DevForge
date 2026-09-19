# DevForge Production Backup & Disaster Recovery Strategy

## 1. Overview
DevForge stores all platform control-plane metadata, application definitions, environment definitions, deployment logs, GitOps sync state, Terraform execution states, Ansible run logs, self-healing remediation events, and user authentication/RBAC records in a dedicated PostgreSQL 16 database (`devforge_db`).

This runbook outlines the operational procedures for backup scheduling, verification, offsite replication, and disaster recovery.

---

## 2. Recovery Objectives
- **Recovery Point Objective (RPO)**: <= 1 hour (Continuous WAL archiving yields RPO <= 5 minutes).
- **Recovery Time Objective (RTO)**: <= 15 minutes to complete restored service readiness.

---

## 3. Data Inventory & Scope
The following critical PostgreSQL relations must be preserved:

| Table | Importance | Description |
|---|---|---|
| `users` | CRITICAL | Platform identity, password hashes, and assigned RBAC roles |
| `applications` | CRITICAL | Managed applications, template metadata, Git references, CI status |
| `provisioning_jobs` | HIGH | Application scaffolding jobs, step states, and generation payload snapshots |
| `deployments` | HIGH | Deployment history, versions, logs, and commit hashes |
| `environments` | HIGH | Cluster endpoints, resource budgets, and environment descriptors |
| `remediation_policies` | CRITICAL | Self-healing policies, approval gates, cooldowns, max retry attempts |
| `remediation_events` | HIGH | Detected incidents, status, attempts count, and audit trails |
| `remediation_executions` | HIGH | Action execution outputs, return codes, and error messages |
| `terraform_runs` | HIGH | Infrastructure plan/apply logs and managed resource counts |
| `ansible_executions` | HIGH | Automation playbook execution results and outputs |
| `gitops_applications` | HIGH | Argo CD application mappings and sync health state |
| `activity` | HIGH | Complete immutable platform audit event stream |

---

## 4. Backup Architecture & Strategy

### Daily Full Logical Backup
Executed daily via automated cron or Kubernetes CronJob:
```bash
# Export compressed PostgreSQL custom format dump
pg_dump \
  -h "${POSTGRES_HOST:-postgres}" \
  -U "${POSTGRES_USER:-devforge}" \
  -d "${POSTGRES_DB:-devforge_db}" \
  -Fc \
  -f "/backups/devforge_db_$(date +%Y%m%d_%H%M%S).dump"
```

### Encryption & Offsite Retention
1. **At-Rest Encryption**: Backups are encrypted with AES-256 (e.g. GPG/KMS).
2. **Retention Policy**:
   - Hourly WAL segments retained for 7 days.
   - Daily snapshots retained for 30 days.
   - Weekly snapshots retained for 12 weeks.
   - Monthly snapshots retained for 12 months.

---

## 5. Recovery & Restore Procedures

### Step 1: Pre-Restore Readiness Verification
Verify PostgreSQL container or cluster is reachable and healthy:
```bash
pg_isready -h localhost -p 5432 -U devforge
```

### Step 2: Database Restoration
To restore into a clean or recovering instance:
```bash
# 1. Create target database if needed
createdb -h localhost -U devforge devforge_db

# 2. Restore using pg_restore with clean schema wipe
pg_restore \
  -h localhost \
  -U devforge \
  -d devforge_db \
  --clean \
  --if-exists \
  --no-owner \
  /backups/devforge_db_latest.dump
```

### Step 3: Platform Integrity Check
After restoration, verify DevForge API readiness:
```bash
# Test readiness probe
curl -f http://localhost:8000/ready

# Output should return:
# {"status": "ready", "service": "DevForge API", "database": "connected"}
```

---

## 6. Disaster Recovery Drill Schedule
- Automated restoration verification tests run weekly in an isolated preview environment.
- Any restore taking longer than the 15-minute RTO threshold triggers an automated alert.
