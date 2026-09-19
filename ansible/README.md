# DevForge Ansible Automation

## 1. Overview
DevForge introduces Ansible Automation to manage configuration baselines, application directory topologies, runtime configuration templates, and operational health checks.

Ansible complements Terraform (infrastructure provisioning) and Kubernetes (runtime scheduling) without competing over resources:
- **Terraform**: Infrastructure & environment resources (Namespaces, base cluster ConfigMaps).
- **Kubernetes**: Runtime scheduling, deployments, pods, services, and routing.
- **Ansible**: Application runtime configuration, filesystem layout, environment directory baselines, and health checks.
- **DevForge IDP**: Control plane orchestration, catalog, CI workflow generation, and GitHub integration.

---

## 2. Directory Structure
```text
ansible/
├── inventories/
│   └── development/
│       └── hosts.yml
├── playbooks/
│   ├── configure_application.yml
│   ├── configure_environment.yml
│   └── health_check.yml
├── roles/
│   └── application/
│       ├── defaults/
│       │   └── main.yml
│       ├── vars/
│       │   └── main.yml
│       ├── tasks/
│       │   └── main.yml
│       ├── handlers/
│       │   └── main.yml
│       └── templates/
│           └── app_config.env.j2
└── README.md
```

---

## 3. Approved Playbooks
Only approved playbooks in the allowlist can be executed via DevForge:
1. `configure_application`: Prepares application runtime directory tree (`/tmp/devforge/apps/<app_name>`), generates idempotent `.env` configuration, and validates structure.
2. `configure_environment`: Establishes environment baseline directories and descriptor marker files (`/tmp/devforge/environments/<env>/environment.json`).
3. `health_check`: Probes system filesystem, environment readiness, and application configuration status.

---

## 4. Idempotency Guarantee
All tasks use declarative Ansible modules (`file`, `template`, `stat`, `assert`, `copy`) rather than ad-hoc shell scripts. Subsequent executions with unchanged inputs produce zero state drift (`changed=0`).

---

## 5. Security & Isolation
- **No Arbitrary Commands**: APIs reject arbitrary playbook paths or shell execution.
- **Local Development**: Uses `ansible_connection: local` without requiring SSH credentials or passwords.
- **No Credentials**: Secrets are never persisted in state, playbooks, or database logs.
