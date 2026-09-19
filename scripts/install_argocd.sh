#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "DevForge - Argo CD Local Cluster Provisioning"
echo "=================================================="

# Check kubectl connection
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "ERROR: Kubernetes cluster is not accessible. Ensure kind or Docker Desktop Kubernetes is running."
    exit 1
fi

echo "✓ Kubernetes cluster reachable."

# Create argocd namespace if not exists
if ! kubectl get namespace argocd > /dev/null 2>&1; then
    echo "Creating namespace 'argocd'..."
    kubectl create namespace argocd
else
    echo "✓ Namespace 'argocd' already exists."
fi

# Apply official Argo CD manifests
echo "Applying Argo CD manifests..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml --server-side --force-conflicts

# Wait for CRD registration
echo "Waiting for Argo CD CRDs to register..."
kubectl wait --for condition=established --timeout=60s crd/applications.argoproj.io || true

# Wait for key deployments
echo "Waiting for Argo CD server and controller rollouts..."
kubectl rollout status deployment/argocd-server -n argocd --timeout=120s || true
kubectl rollout status deployment/argocd-repo-server -n argocd --timeout=120s || true
kubectl rollout status deployment/argocd-applicationset-controller -n argocd --timeout=120s || true

echo "=================================================="
echo "✓ Argo CD provisioned successfully in local cluster."
echo "=================================================="
