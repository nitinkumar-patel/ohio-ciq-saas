terraform {
  required_version = "= 1.14.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.100.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "= 2.8.0"
    }
  }
}

provider "aws" {
  region              = "us-east-2"
  allowed_account_ids = ["910929919874"]
}
