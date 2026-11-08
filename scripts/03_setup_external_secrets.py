#!/usr/bin/env python3
"""Wire dev External Secrets to the IAM role belonging to the current cluster."""
from dev_cluster import REGION, apply_object, apply_practice_namespace, refresh_dev_kubeconfig, run


def main():
    cluster = refresh_dev_kubeconfig()
    account = cluster["arn"].split(":")[4]
    role = f"arn:aws:iam::{account}:role/pharma-dev-eso-role"
    apply_practice_namespace()
    run(["kubectl", "annotate", "serviceaccount", "external-secrets", "-n", "external-secrets",
         f"eks.amazonaws.com/role-arn={role}", "--overwrite"])
    run(["kubectl", "rollout", "restart", "deployment/external-secrets", "-n", "external-secrets"])
    run(["kubectl", "rollout", "status", "deployment/external-secrets", "-n", "external-secrets", "--timeout=180s"])
    run(["kubectl", "wait", "--for=condition=Established", "crd/clustersecretstores.external-secrets.io",
         "crd/externalsecrets.external-secrets.io", "--timeout=60s"])
    apply_object({"apiVersion": "external-secrets.io/v1", "kind": "ClusterSecretStore",
                  "metadata": {"name": "aws-secrets-manager"}, "spec": {"provider": {"aws": {
                      "service": "SecretsManager", "region": REGION, "auth": {"jwt": {
                          "serviceAccountRef": {"name": "external-secrets", "namespace": "external-secrets"}}}}}}})
    for name, fields in (("db-credentials", {"DB_USERNAME": "username", "DB_PASSWORD": "password", "DB_HOST": "host"}),
                         ("jwt-secret", {"JWT_SECRET": "secret"})):
        apply_object({"apiVersion": "external-secrets.io/v1", "kind": "ExternalSecret",
                      "metadata": {"name": name, "namespace": "dev"}, "spec": {
                          "refreshInterval": "1m", "secretStoreRef": {"name": "aws-secrets-manager", "kind": "ClusterSecretStore"},
                          "target": {"name": name, "creationPolicy": "Owner"}, "data": [
                              {"secretKey": key, "remoteRef": {"key": f"/pharma/dev/{name}", "property": field}}
                              for key, field in fields.items()]}})
    run(["kubectl", "wait", "--for=condition=Ready", "clustersecretstore/aws-secrets-manager", "--timeout=120s"])
    run(["kubectl", "wait", "--for=condition=Ready", "externalsecret/db-credentials",
         "externalsecret/jwt-secret", "-n", "dev", "--timeout=120s"])
    print("Dev secrets synced, including the current RDS hostname. Next: build images, then run 05_deploy_services.py.")
    print("If an existing application's DB_HOST changed, restart its deployment to reload environment variables.")


if __name__ == "__main__":
    main()
