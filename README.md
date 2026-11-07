# Pharma infrastructure

Terraform roots live in `env/dev`, `env/staging`, and `env/prod`. Each uses its
own S3 state key in `pharma-terraform-state-tarak` in `ap-south-1`.

## Toolchain and local checks

Use **Terraform 1.15.9**, matching `.github/workflows/terraform.yml`. Terraform
1.9 cannot initialize this configuration: the roots require at least 1.15.0,
the RDS module uses write-only passwords, and the S3 backend uses native lockfiles.

From the repository root, these checks do not access the remote state or create
AWS resources:

```bash
terraform fmt -check -recursive
for environment in dev staging prod; do
  terraform -chdir="env/$environment" init -backend=false -input=false -lockfile=readonly
  terraform -chdir="env/$environment" validate -no-color
done
```

The committed `.terraform.lock.hcl` files keep provider versions consistent
between plan and apply. The shared modules also pin their upstream releases.
To intentionally update dependencies, change the module pins if needed, run
`terraform init -backend=false -upgrade` in each root, and review/commit the
resulting lockfile changes. Never commit state, saved plans, or secret tfvars.

## GitHub Actions inputs

The plan job needs these **repository-level Actions secrets** (or organization
secrets available to this repository). It does not attach to an approval
environment, so environment-only secrets are not available to that job.

| Purpose | dev | staging | prod |
| --- | --- | --- | --- |
| RDS password | `DEV_DB_PASSWORD` | `STAGING_DB_PASSWORD` | `PROD_DB_PASSWORD` |
| JWT signing secret | `DEV_JWT_SECRET` | `STAGING_JWT_SECRET` | `PROD_JWT_SECRET` |

The existing authentication configuration uses `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY`. Set the `GH_ORG` repository variable to the owner of
the frontend/backend repositories; it defaults to the infrastructure repository
owner when unset. Secret values are passed through `TF_VAR_*` environment
variables, not inserted into shell commands.

- Pull requests validate all three roots and plan **dev** only.
- Pushes to `main` validate all roots, plan dev, and enter the dev apply job.
- Manual `plan` and `apply` use `target_env`.
- Manual `destroy` uses `target_env`; the existing `destroy-staging` and
  `destroy-prod` aliases always select their named environment.
- Every destroy action requires `confirm_destroy=destroy` and skips the normal
  plan job. Apply/destroy jobs use the selected GitHub environment; configure
  required reviewers on `dev`, `staging`, and `prod` to enforce approval.

The saved plan is retained for one day and applied using the same locked
dependencies. Plans contain sensitive values; restrict repository/artifact
access accordingly.

## RDS backup retention and interrupted applies

Dev defaults to **1 day** of automated RDS backups because this account rejected
the previous 7-day setting with `FreeTierRestrictionError`. Staging and prod
retain their 7-day defaults. Each root passes `backup_retention_period` to the
RDS module, so an intentional override now takes effect. A retention period of
0 disables automated backups; the dev default keeps them enabled with a shorter
recovery window. Account-plan limits are checked by AWS during creation and
may not be caught by `terraform plan`.

After a partial apply, run a **new** plan and apply from the corrected commit.
Terraform refreshes the existing state and plans the remaining work. Do not
reuse the failed run's saved plan or destroy successfully created resources to
retry database creation. On GitHub Actions, merging the fix starts the existing
main/dev plan-and-apply flow; a manual `apply` with `target_env=dev` also creates
a fresh plan first.

## State locking

Runs targeting the same environment are serialized across branches, and a new
run does not cancel an active apply. Terraform waits up to five minutes for a
state lock. The workflow never deletes `.tflock` objects on failure.

If Terraform reports a stale lock, first establish that the owning run/process
has stopped. Initialize the affected root, then use `terraform force-unlock`
with the exact lock ID from the error. Do not delete a lock belonging to an
active run.
