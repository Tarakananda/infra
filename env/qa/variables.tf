variable "db_password" {
  description = "Master password for the RDS PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT signing secret for the application"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub username or organization that owns frontend and backend"
  type        = string
  default     = "Tarakananda"
}

variable "backup_retention_period" {
  description = "Days to retain automated RDS backups; use a short retention period for the dev free-plan account"
  type        = number
  default     = 1

  validation {
    condition     = var.backup_retention_period == 1
    error_message = "The dev practice profile keeps one day of backups for this account's free-plan restriction."
  }
}

variable "eks_admin_principal_arns" {
  description = "Additional IAM user/role ARNs allowed to administer the dev cluster (for example your local CLI identity). Do not use STS session ARNs."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for arn in var.eks_admin_principal_arns : can(regex("^arn:aws:iam::[0-9]{12}:(user|role)/.+$", arn))])
    error_message = "Use persistent IAM user or role ARNs, not assumed-role session ARNs."
  }
}
