#!/usr/bin/env python3
"""Check the selected dev applications and readiness without requiring an ALB."""
import json
from dev_cluster import refresh_dev_kubeconfig, run


def main():
    refresh_dev_kubeconfig()
    errors = []
    apps = json.loads(run(["kubectl", "get", "applications", "-n", "argocd", "-o", "json"], capture=True))["items"]
    apps = [app for app in apps if app.get("spec", {}).get("project") == "pharma"]
    if not apps:
        errors.append("No pharma applications deployed; run 05_deploy_services.py.")
    for app in apps:
        status = app.get("status", {})
        sync = status.get("sync", {}).get("status", "Unknown")
        health = status.get("health", {}).get("status", "Unknown")
        print(f"{app['metadata']['name']}: {sync}, {health}")
        if sync != "Synced" or health != "Healthy":
            errors.append(f"{app['metadata']['name']} is not Synced/Healthy.")
    pods = json.loads(run(["kubectl", "get", "pods", "-n", "dev", "-o", "json"], capture=True))["items"]
    if apps and not pods:
        errors.append("No dev pods found.")
    for pod in pods:
        status = pod.get("status", {})
        ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in status.get("conditions", []))
        if status.get("phase") != "Succeeded" and not ready:
            errors.append(f"Pod {pod['metadata']['name']} is not Ready.")
    secrets = json.loads(run(["kubectl", "get", "externalsecrets", "-n", "dev", "-o", "json"], capture=True))["items"]
    ready_secrets = {s["metadata"]["name"] for s in secrets if any(
        c.get("type") == "Ready" and c.get("status") == "True" for c in s.get("status", {}).get("conditions", []))}
    for name in ("db-credentials", "jwt-secret"):
        if name not in ready_secrets:
            errors.append(f"ExternalSecret {name} is not Ready.")
    services = json.loads(run(["kubectl", "get", "services", "-A", "-o", "json"], capture=True))["items"]
    for service in services:
        if service["spec"].get("type") == "LoadBalancer":
            errors.append(f"Unexpected chargeable LoadBalancer service: {service['metadata']['name']}")
    ingresses = json.loads(run(["kubectl", "get", "ingresses", "-A", "-o", "json"], capture=True))["items"]
    if ingresses:
        errors.append("Ingress resources exist; this practice profile uses port-forward only.")
    for error in errors:
        print("FAIL: " + error)
    print("All readiness checks passed." if not errors else f"{len(errors)} check(s) failed.")
    print("For browser/HTTP testing, port-forward the specific service; readiness is not an HTTP end-to-end test.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
