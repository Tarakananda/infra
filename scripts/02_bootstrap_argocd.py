#!/usr/bin/env python3
"""Register your GitOps repository and the dev-only Argo CD project."""
import getpass
import os
from dev_cluster import (ROOT, REPO_PLACEHOLDER, apply_object, apply_practice_namespace,
                         refresh_dev_kubeconfig, run, validate_repo_url)


def main():
    refresh_dev_kubeconfig()
    run(["kubectl", "get", "deployment", "argocd-server", "-n", "argocd"], capture=True)
    url = validate_repo_url(os.environ.get("GITOPS_REPO_URL") or input("GitOps repository HTTPS URL: ").strip())
    username = os.environ.get("GITHUB_USERNAME") or input("GitHub username [blank for public repository]: ").strip()
    token = os.environ.get("GITOPS_TOKEN", "")
    if username and not token:
        token = getpass.getpass("Read-only GitHub token [hidden]: ")
    if username and not token:
        raise SystemExit("A token is required when a repository username is provided.")
    # Secret contents travel via stdin, never command arguments or log output.
    data = {"type": "git", "url": url}
    if username:
        data.update(username=username, password=token)
    apply_object({"apiVersion": "v1", "kind": "Secret", "metadata": {
        "name": "zen-gitops-repo", "namespace": "argocd",
        "labels": {"argocd.argoproj.io/secret-type": "repository"}}, "stringData": data})
    apply_practice_namespace()
    template = (ROOT / "zen-gitops/argocd/projects/pharma-project.yaml").read_text()
    run(["kubectl", "apply", "-f", "-"], input=template.replace(REPO_PLACEHOLDER, url))
    print(f"Registered {url} for the dev namespace. Next: python3 scripts/03_setup_external_secrets.py")


if __name__ == "__main__":
    main()
