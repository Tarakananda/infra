output "vpc_id" {
  description = "ID of the VPC"
  value = module.vpc.vpc_id
}

output "private_subnets" {
  description = "ID of private subnet cidr"
  value = module.vpc.private_subnets
}

output "public_subnets" {
  description = "ID of public subnet cidr"
  value = module.vpc.public_subnets
}

output "database_subnets" {
  description = "ID of database subnet cidr"
  value = module.vpc.database_subnets
}

output "database_subnet_group_name" {
  description = "Name of the database subnet group"
  value = module.vpc.database_subnet_group_name
}
