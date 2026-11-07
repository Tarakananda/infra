terraform {
  backend "s3" {
    bucket       = "pharma-terraform-state-tarak"
    key          = "env/prod/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}