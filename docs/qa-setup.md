# QA pipeline setup

## GitHub inputs

Open https://github.com/Tarakananda/infra/settings/environments and create or select `qa`.
Under **Environment secrets**, add:

| Name | Value |
| --- | --- |
| `QA_DB_PASSWORD` | A new random QA database password. Generate locally with `openssl rand -hex 16` (32 characters). |
| `QA_JWT_SECRET` | A separate random signing secret. Generate locally with `openssl rand -hex 32` (64 characters). |

Paste only each generated value into its GitHub secret. Do not commit values or send them in chat.
For an existing QA database, use its current password; changing an existing database password also requires incrementing the RDS module's `password_version` input.

The workflow retains AWS access-key authentication. Existing repository secrets `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are inherited by QA jobs. If absent, configure them at Settings → Secrets and variables → Actions, using the AWS IAM identity authorized to manage this infrastructure. These are AWS-issued credentials, not passwords you invent. Environment secrets with the same names override repository secrets.

Under **Environment variables**, optionally add `QA_EKS_ADMIN_PRINCIPAL_ARNS` as a JSON array of persistent IAM user/role ARNs, for example `["arn:aws:iam::123456789012:user/your-user"]`. Use the real ARN from `aws sts get-caller-identity`; do not use an STS assumed-role session ARN. Without this variable, additional local administrators are not configured; the cluster creator still receives access.

`GH_ORG` is optional and defaults to the repository owner.

## Shared-resource prerequisites

QA reads the nine existing ECR repositories and reuses the account's `token.actions.githubusercontent.com` OIDC provider. Dev retains ownership of these resources. They must exist in the AWS account (ECR in ap-south-1) before the QA plan/apply. Do not import the same resources into both states. Do not destroy their owning dev stack while QA depends on them; move shared resources to a dedicated stack before requiring independent dev teardown.

The S3 bucket `pharma-terraform-state-tarak` must already exist. QA uses the separate `env/qa/terraform.tfstate` key. The workflow identity needs access to that state and its S3 lock object as well as permissions to manage the planned resources.

This change assumes QA has not previously applied/imported the removed ECR module or its own GitHub OIDC provider. If QA state already owns either, stop and reconcile ownership before apply; removing managed resources from configuration can otherwise plan deletions.

## Run and verify

1. Set the GitHub inputs above and merge the fix PR.
2. Open Actions → Terraform QA Infrastructure → Run workflow → branch `main` → action `plan`.
3. Confirm validation, all Python tests, AWS plan, and the QA capacity check pass. Review the plan for unexpected deletions/replacements.
4. Run action `apply` only when ready to create QA infrastructure. This incurs additional AWS charges alongside dev.
5. Connect locally using `aws eks update-kubeconfig --region ap-south-1 --name pharma-qa-cluster --alias pharma-qa --user-alias pharma-qa`, then use `kubectl --context pharma-qa` explicitly.

The older `connect_dev.py` and bootstrap helpers remain dev-only. This infrastructure workflow does not install QA ArgoCD/controllers or deploy application workloads.

Keep `env/qa/.terraform.lock.hcl` committed. If provider requirements change, generate the lockfile with `terraform -chdir=env/qa init -backend=false -input=false`, then add Linux checksums with `terraform -chdir=env/qa providers lock -platform=linux_amd64`, review and commit it. CI keeps `-lockfile=readonly`.
