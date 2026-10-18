variable "project_name" {
  description = "Name of the Project"
  type = string
}

variable "env_name" {
  description = "Name of the environment"
  type = string
}

variable "oidc_provider_arn" {
  description = "ARN of the EKS OIDC Provider"
  type = string
}

varibale "oidc_provider_url" {
  description = "URL of the EKS OIDC Provider"
  type = string
}

variable "aws_account_id" {
  descriotion = "AWS Account ID"
  type = string
}

variable "github_org" {
  description = "GitHub username"
  type = string
}
