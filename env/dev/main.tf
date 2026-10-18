locals {
  project_name = "zen-pharma"
  env_name = "dev"
  region = "ap-south-1"
}

data "aws_caller_identity" "current" {}

module "vpc" {
  source = "../../modules/vpc"
  
  project_name = local.project_name
  env_name = local.env_name
  region = local.region
  vpc_cidr = "10.0.0.0/16"
  public_subnet_cidr = ["10.0.1.0/24" , "10.0.2.0/24"]
  private_subnet_cidr = ["10.0.3.0/24" , "10.0.4.0/24"]
  database_subnet_cidr = ["10.0.5.0/24" , "10.0.6.0/24"]
}
