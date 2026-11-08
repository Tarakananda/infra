#!/usr/bin/env python3
"""Install the small dev Argo CD and External Secrets deployments."""
from dev_cluster import ROOT, apply_practice_namespace, refresh_dev_kubeconfig, require_tools, run


def main():
    require_tools("helm")
    refresh_dev_kubeconfig()
    apply_practice_namespace()
    for name, url in (("argo", "https://argoproj.github.io/argo-helm"),
                      ("external-secrets", "https://charts.external-secrets.io")):
        run(["helm", "repo", "add", name, url, "--force-update"])
    run(["helm", "repo", "update"])
    run(["helm", "upgrade", "--install", "argocd", "argo/argo-cd", "-n", "argocd",
         "--create-namespace", "-f", ROOT / "zen-gitops/helm/argocd-dev-values.yaml",
         "--wait", "--timeout", "10m"])
    run(["helm", "upgrade", "--install", "external-secrets", "external-secrets/external-secrets",
         "-n", "external-secrets", "--create-namespace", "--set", "installCRDs=true",
         "--set", "serviceAccount.name=external-secrets", "--set", "replicaCount=1",
         "--wait", "--timeout", "10m"])
    print("Argo CD and External Secrets installed. Next: python3 scripts/02_bootstrap_argocd.py")
    print("Argo CD UI: python3 scripts/connect_dev.py -- kubectl -n argocd port-forward svc/argocd-server 8080:443")
    print("Open https://localhost:8080. Username: admin. Retrieve the initial password locally:")
    print("kubectl --context pharma-dev -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 --decode")
    print("This practice profile uses ClusterIP/port-forward and does not install an ALB controller.")


if __name__ == "__main__":
    main()
