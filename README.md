# Pharma dev practice lab

This repository now manages **dev only**, in **ap-south-1 (Mumbai)**. It is a
small learning environment with one worker, one database and no public load
balancers. Pull requests and merges **plan only**; a merge no longer starts
billable infrastructure automatically.

## Cost target: below $0.50/hour for light practice

The configured idle baseline is approximately **$0.296/hour**, rounded to
**$0.30/hour before tax and usage charges**. This is an estimate, not an AWS
spending cap. No free-tier credits, reservations or Spot discounts are assumed.
Prices were checked on 8 November 2026; monthly storage/key/secret prices below
are divided by 730 hours to make the comparison consistent.

| Resource | Dev configuration | Estimated USD/hour |
| --- | --- | ---: |
| EKS control plane | Kubernetes 1.36, STANDARD support | 0.1000 |
| Worker | 1 × m7i-flex.large, on-demand, 2 vCPU / 8 GiB | 0.10075 |
| NAT gateway | 1 gateway for private nodes | 0.0560 |
| Public IPv4 | 1 NAT Elastic IP | 0.0050 |
| RDS PostgreSQL | 1 × db.t3.micro, single AZ | 0.0260 |
| Worker storage | 20 GiB gp3 at $0.0912/GiB-month | 0.0025 |
| Database storage | 20 GiB gp3 at $0.131/GiB-month | 0.0036 |
| KMS key + Secrets Manager | 1 key + 2 secrets | 0.0025 |
| **Baseline** | | **0.2963** |

Sources: [EKS pricing](https://aws.amazon.com/eks/pricing/),
[AWS Mumbai EC2/EBS/NAT price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-south-1/index.csv),
[AWS Mumbai RDS price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/ap-south-1/index.json),
[AWS Mumbai IPv4 price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/ap-south-1/index.json),
[free-plan instance eligibility](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html),
[KMS pricing](https://aws.amazon.com/kms/pricing/),
[Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/).

NAT processing ($0.056/GB), internet/cross-AZ transfer, RDS burst CPU credits,
ECR image storage, S3 state/version storage and API requests are additional.
RDS T3 uses unlimited CPU credits; sustained database load can add charges.
Taxes and resources elsewhere in your AWS account are also outside the baseline.
The remaining ~$0.20/hour is headroom, not a guaranteed allowance. AWS Budgets
alerts are delayed and do not impose a real-time $0.50/hour cap. If you need an
absolute spending ceiling, this metered AWS deployment cannot guarantee it.

Cost controls included here:

- EKS 1.33 was in extended support ($0.60/hour for the control plane alone).
  EKS 1.36 uses standard support ($0.10/hour). `support_type = "STANDARD"`
  disables paid extended support. AWS will eventually auto-upgrade the control
  plane; review this version pin, worker version and add-ons before **2 August
  2027**, the published end of standard support. CI blocks an expired profile.
- Worker minimum, desired and maximum are all **1**. The M7i-flex worker has
  no T-series CPU credit surcharges and is on the current free-plan eligible
  instance list. `MINIMAL` updates avoid extra upgrade nodes and cause
  downtime in this single-node lab. Node version updates may force eviction when
  disruption budgets block draining the only node. There is no cluster autoscaler
  or Fargate.
- One 20 GiB worker disk; one 20 GiB database with storage autoscaling disabled.
  RDS keeps **one day** of automated backups, preserving the fix for this
  account's `FreeTierRestrictionError`.
- One NAT gateway and a free S3 gateway endpoint to bypass NAT processing for
  regional S3/ECR image layers. Control-plane CloudWatch logs are disabled.
- Argo CD and applications use ClusterIP services and local port-forwarding.
  The installer does not install an ALB controller. The dev ResourceQuota blocks
  LoadBalancer services and Ingress objects; the Argo CD project also disallows
  Ingress and changes to the quota. These controls cover this lab, not manual
  changes elsewhere in AWS or Kubernetes.
- ECR retains the last three images per repository. Manual destroy removes
  repository images too, so a non-empty registry does not block teardown.
- CI checks the Terraform plan for the reviewed capacity profile before apply;
  it is not a usage-based billing estimator.

Use one replica per application and small memory/CPU requests in your separate
GitOps repository. Eight GiB is shared by Kubernetes, controllers and your apps;
if all nine services do not fit, practice with a subset. The lab is not highly
available and is not suitable for production.

## Start, connect and stop

1. Merge this change, then open **Actions → Terraform Infrastructure → Run
   workflow**, choose **main**, and set `action=apply`. Every apply creates a
   new plan and applies that run's checked plan. A push/merge only plans.
2. After apply succeeds, pull the repository on your computer and run:

   ```bash
   python3 scripts/connect_dev.py
   ```

3. Install and configure the dev controllers:

   ```bash
   python3 scripts/01_install_prerequisites.py
   python3 scripts/02_bootstrap_argocd.py
   python3 scripts/03_setup_external_secrets.py
   ```

4. Build/push your application images using their own pipelines (the optional
   `04_run_pipeline.py` helper prompts for those repositories). Then select the
   services to deploy:

   ```bash
   python3 scripts/05_deploy_services.py pharma-ui
   # Or: python3 scripts/05_deploy_services.py all
   python3 scripts/06_verify_deployment.py
   ```

   Script 02 asks for your actual GitOps repository URL and optional private-repo
   credentials. Script 05 reads that registered URL, so it cannot silently point
   at someone else's repository. Your GitOps repository must contain the service
   paths used in `zen-gitops/argocd/apps/dev`, with **ClusterIP services**, no
   Ingress, and dev-sized replicas/resources. The infra repository contains
   Application templates, not the application's Deployment/Service manifests.

5. Access Argo CD or your app without a billable ALB:

   ```bash
   python3 scripts/connect_dev.py -- kubectl -n argocd port-forward svc/argocd-server 8080:443
   # In another terminal, for a pharma-ui Service exposing port 80:
   python3 scripts/connect_dev.py -- kubectl -n dev port-forward svc/pharma-ui 8081:80
   ```

   Open `https://localhost:8080` for Argo CD and `http://localhost:8081` for the
   UI. Use the Service's actual port if your GitOps manifest differs. A UI whose
   API base URL previously used an ALB also needs a reachable local API route
   configured in that separate application repository.

6. After practice, run the workflow with **`action=destroy`** and
   **`confirm_destroy=destroy`**. This deletes the dev database without a final
   snapshot and deletes practice ECR images. Check that the job succeeds. A
   stopped/idle worker does not stop EKS or NAT hourly charges. The existing S3
   state bucket and any unrelated resources remain and may still cost money.

## Why the endpoint became stale

Recreating EKS changes both its API endpoint and certificate authority. The old
installer continued using the existing kubeconfig when `update-kubeconfig`
failed, and the remaining scripts never refreshed it. Region prompts also
previously defaulted to `us-east-1`, while Terraform creates Mumbai resources.

All Kubernetes scripts now describe the live `pharma-dev-cluster` in
`ap-south-1`, refresh the stable **pharma-dev** context, compare its endpoint and
CA with AWS, and verify node access before making Kubernetes changes. A failed
refresh or authorization check stops execution. Commands are explicitly bound
to that context. The first `KUBECONFIG` file is used when set; otherwise the
usual `~/.kube/config` is updated. `connect_dev.py --kubeconfig PATH` selects a
specific file.

GitHub Actions refreshes the **runner's** kubeconfig and displays current EKS/RDS
endpoints in the run summary. It cannot modify your Mac's kubeconfig: run
`python3 scripts/connect_dev.py` after each apply, or use any of the Kubernetes
scripts, which refresh automatically. A plain `kubectl` command does not perform
this refresh. Install AWS CLI v2, Helm, Python 3 and a kubectl version within one
minor of the cluster. Authenticate the AWS CLI to the account used by Actions.

The Terraform caller gets an EKS cluster-admin access entry. If your local CLI
uses a different IAM identity, set repository variable
`DEV_EKS_ADMIN_PRINCIPAL_ARNS` to a JSON list of its **IAM user/role ARN(s)** before
applying. Do not duplicate the Terraform caller and do not use STS session ARNs.
For role-based Kubernetes access, use
`python3 scripts/connect_dev.py --role-arn arn:aws:iam::<account>:role/<role>`
(or `EKS_ROLE_ARN`). Your current CLI identity still needs `eks:DescribeCluster`;
the role must already be allowed to access the cluster. Refreshing an endpoint
does not grant permissions.

Terraform writes the current RDS hostname to Secrets Manager. External Secrets
refreshes it every minute. Applications using environment variables must be
restarted after an existing database endpoint changes:

```bash
python3 scripts/connect_dev.py -- kubectl -n dev rollout restart deployment/<service>
```

## GitHub configuration and checks

Required repository secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`DEV_DB_PASSWORD`, `DEV_JWT_SECRET`. Optional repository variables: `GH_ORG`
(defaults to the repository owner) and `DEV_EKS_ADMIN_PRINCIPAL_ARNS` (defaults
to `[]`). Apply and destroy use the GitHub **dev** environment. Secrets needed
by the plan must be repository-level or organization-level, not only attached
to an environment.

Use **Terraform 1.15.9**, matching Actions. Provider lockfiles and module versions
are pinned. Do not commit state, saved plans or secret tfvars. Local checks:

```bash
terraform fmt -check -recursive
terraform -chdir=env/dev init -backend=false -input=false -lockfile=readonly
terraform -chdir=env/dev validate -no-color
python3 -m unittest discover -s tests -v
```

Plans are retained for one day and contain sensitive values; restrict artifact
access. All dev operations share one concurrency group and wait up to five
minutes for state locks. Never delete an active lock. For a confirmed stale
lock, initialize `env/dev` and use `terraform force-unlock` with the exact lock ID.
After a partial apply, start a new apply run so Terraform refreshes state and
plans the remaining work.

## Migration from the previous configuration

The latest dev destroy completed before this change was prepared; the next
apply is expected to create a fresh 1.36 cluster. If you have since recreated a
1.33 cluster, do not attempt a direct 1.33 → 1.36 in-place upgrade. EKS upgrades
must proceed one minor at a time, and extended support can only be disabled
once the cluster reaches standard support. Review the plan before proceeding.

The staging/prod Terraform roots and workflow choices are removed. **Removing
source files does not delete resources in their separate state files.** If you
ever deployed those environments, use the previous configuration at commit
`86266cc3fc61301e527f332145f4fc4c84df6466` to inspect and intentionally destroy
them separately. This PR does not touch those AWS states or change your app
repositories.
