"""Shared dev-only connection and command helpers (Python standard library only)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGION = "ap-south-1"
CLUSTER = "pharma-dev-cluster"
CONTEXT = "pharma-dev"
NAMESPACE = "dev"
REPO_PLACEHOLDER = "https://github.com/your-github-username/zen-gitops.git"


def require_tools(*names):
    missing = [name for name in names if not shutil.which(name)]
    if missing:
        raise SystemExit("Install the required tools first: " + ", ".join(missing))


def run_process(args, **kwargs):
    """Always bind kubectl/Helm operations to the verified dev context."""
    args = list(map(str, args))
    if args[0] in ("kubectl", "helm"):
        forbidden = ("--context", "--kube-context", "--kubeconfig", "--server")
        if any(arg.split("=", 1)[0] in forbidden for arg in args[1:]):
            raise SystemExit("Connection overrides are not allowed; use the verified pharma-dev context.")
        flag = "--context" if args[0] == "kubectl" else "--kube-context"
        args[1:1] = [flag, CONTEXT]
    return subprocess.run(args, **kwargs)


def run(args, *, capture=False, input=None):
    result = run_process(args, text=True, capture_output=capture, input=input)
    if result.returncode:
        detail = (result.stderr or "").strip() if capture else ""
        raise SystemExit(f"{args[0]} failed (exit {result.returncode}). {detail}")
    return result.stdout.strip() if capture else None


def refresh_dev_kubeconfig(*, role_arn=None, kubeconfig=None, verify=True):
    """Fetch the live endpoint and CA every time; never fall back to an old context."""
    require_tools("aws", "kubectl")
    for name, expected in (("ENV", NAMESPACE), ("CLUSTER_NAME", CLUSTER)):
        if os.environ.get(name, expected) != expected:
            raise SystemExit(f"This project supports dev only. Unset {name} or set it to {expected}.")
    # An unrelated default AWS region on a developer's laptop must not select a stale cluster.
    os.environ["AWS_REGION"] = REGION
    os.environ["AWS_DEFAULT_REGION"] = REGION
    cluster = json.loads(run([
        "aws", "eks", "describe-cluster", "--region", REGION, "--name", CLUSTER,
        "--output", "json", "--no-cli-pager",
    ], capture=True))["cluster"]
    if cluster["name"] != CLUSTER or cluster["status"] != "ACTIVE":
        raise SystemExit("The dev cluster is not ACTIVE. Finish Terraform apply, then reconnect.")
    config_path = Path(kubeconfig or os.environ.get("KUBECONFIG", "").split(os.pathsep)[0]
                       or Path.home() / ".kube" / "config").expanduser().absolute()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["aws", "eks", "update-kubeconfig", "--region", REGION, "--name", CLUSTER,
               "--alias", CONTEXT, "--user-alias", CONTEXT, "--kubeconfig", str(config_path)]
    role_arn = role_arn or os.environ.get("EKS_ROLE_ARN")
    if role_arn:
        command.extend(["--role-arn", role_arn])
    run(command, capture=True)  # Any failure stops before a kubectl/Helm operation.
    os.environ["KUBECONFIG"] = str(config_path)
    config = json.loads(run(["kubectl", "config", "view", "--minify", "--raw", "-o", "json"], capture=True))
    entries = config.get("clusters", [])
    actual = entries[0]["cluster"] if len(entries) == 1 else {}
    if (actual.get("server") != cluster["endpoint"] or
            actual.get("certificate-authority-data") != cluster["certificateAuthority"]["data"]):
        raise SystemExit("Kubeconfig endpoint/CA does not match the live EKS cluster. No changes made to Kubernetes.")
    if verify:
        # Check both connectivity and the caller's Kubernetes authorization.
        run(["kubectl", "--request-timeout=20s", "get", "nodes", "-o", "name"], capture=True)
    print(f"Connected: {CLUSTER} | {REGION} | context {CONTEXT}\nEndpoint: {cluster['endpoint']}")
    return cluster


def apply_object(obj):
    run(["kubectl", "apply", "-f", "-"], input=json.dumps(obj))


def apply_practice_namespace():
    run(["kubectl", "apply", "-f", ROOT / "zen-gitops/k8s/dev/practice-namespace.yaml"])


def validate_repo_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "github.com" or parts.query or
            parts.fragment or len(parts.path.strip("/").split("/")) != 2 or
            any(c.isspace() or c in '\"\'<>`' for c in url)):
        raise SystemExit("Use an HTTPS GitHub repository URL without credentials or query parameters.")
    return url
