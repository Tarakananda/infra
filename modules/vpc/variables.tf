variable "project_name" {
  description = "Name of the Project"
  type = string
}

variable "env_name" {
  description = "Name of he environment (dev,staging,prod)"
  type = string
}

variable "region" {
  description = "region where the deployments are created"
  type = string
  default = "ap-south-1"
}

variable "vpc_cidr" {
  description = "ID of the VPC"
  type = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "subnets of public cidr blocks"
  type = list(string)
}

variable "private_subnet_cidr" {
  description = "subnets of private cidr blocks"
  type = list(string)
}

variable "database_subnet_cidr" {
  description = "subnets of database cidr blocks"
  type = list(string)
}
