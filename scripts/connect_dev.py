#!/usr/bin/env python3
"""Refresh your local endpoint after every apply, optionally run a dev command."""
import argparse
from dev_cluster import refresh_dev_kubeconfig, run_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role-arn", help="Authorized IAM role to use for Kubernetes authentication")
    parser.add_argument("--kubeconfig", help="Kubeconfig path to update")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Optional -- kubectl/helm command")
    args = parser.parse_args()
    refresh_dev_kubeconfig(role_arn=args.role_arn, kubeconfig=args.kubeconfig)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if command:
        if command[0] not in ("kubectl", "helm"):
            parser.error("Only kubectl or helm commands are supported.")
        return run_process(command).returncode
    print("Kubeconfig refreshed. Run kubectl --context pharma-dev get nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
