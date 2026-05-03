terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Bucket / table names come from -backend-config or terraform/backend.hcl
  # (created once via the bootstrap module).
  backend "s3" {
    key     = "discord-bot/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.region
}

# Latest Amazon Linux 2023 ARM64 AMI.
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }
}
