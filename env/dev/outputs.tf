output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Current EKS API endpoint; changes when the cluster is recreated"
  value       = module.eks.cluster_endpoint
}

output "aws_region" {
  value = local.region
}

output "eso_role_arn" {
  value = module.iam.eso_role_arn
}

output "connect_command" {
  description = "Run on your own computer after every apply/recreation"
  value       = "python3 scripts/connect_dev.py"
}
