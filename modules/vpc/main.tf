module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~>6.0"

  name = "${var.project_name}-${var.env_name}-vpc"
  cidr = "${var.vpc_cidr}"

  azs = ["${var.region}a","${var.region}b"]
  public_subnets = var.public_subnet_cidr
  private_subnets = var.private_subnet_cidr
  database_subnets = var.private_subnet_cidr


  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true
  enable_dns_support = true
  create_database_subnet_group = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.env_name}-cluster" = "owned"
  }

  tags = {
    project = var.project_name
    Env = var.env_name
  }
}
