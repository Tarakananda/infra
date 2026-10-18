terraform {
  required_version = ">=1.11.0"

  required_providers {
  aws = {
    source = "hashicorp/aws"
    version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
  
  default_tags {
  tags = {
    Project = "pharma"
    env = "Dev"
    ManagedBy = "terraform"
    }
  }
}
