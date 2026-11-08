#!/usr/bin/env python3
"""Sync selected applications to dev using the repository registered by script 02."""
import argparse
import base64
from dev_cluster import (ROOT, REPO_PLACEHOLDER, apply_practice_namespace,
                         refresh_dev_kubeconfig, run, validate_repo_url)

SERVICES = ("auth-service", "drug-catalog-service", "inventory-service", "supplier-service",
            "manufacturing-service", "notification-service", "qc-service", "api-gateway", "pharma-ui")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("services", nargs="*", help="Service names, or all; prompts when omitted")
    args = parser.parse_args()
    selected = args.services
    if not selected:
        print("Available services: " + ", ".join(SERVICES))
        selected = input("Services separated by spaces (or all): ").split()
    if selected == ["all"]:
        selected = list(SERVICES)
    if not selected or any(name not in SERVICES for name in selected):
        parser.error("Select service names from: " + ", ".join(SERVICES))
    refresh_dev_kubeconfig()
    encoded = run(["kubectl", "get", "secret", "zen-gitops-repo", "-n", "argocd",
                   "-o", "jsonpath={.data.url}"], capture=True)
    url = validate_repo_url(base64.b64decode(encoded).decode())
    apply_practice_namespace()
    for name in selected:
        path = ROOT / f"zen-gitops/argocd/apps/dev/{name}-app.yaml"
        run(["kubectl", "apply", "-f", "-"], input=path.read_text().replace(REPO_PLACEHOLDER, url))
    print("Applications submitted. Argo CD sync continues asynchronously; verify with 06_verify_deployment.py.")
    print("Use one replica per application and ClusterIP services in your GitOps repository.")
    print("UI access: python3 scripts/connect_dev.py -- kubectl -n dev port-forward svc/pharma-ui 8081:80")


if __name__ == "__main__":
    main()
