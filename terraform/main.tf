terraform {
  required_version = ">= 1.15"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Bucket name comes from -backend-config or terraform/backend.hcl
  # (created once via the bootstrap module).
  backend "s3" {
    key          = "discord-bot/terraform.tfstate"
    use_lockfile = true
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

resource "aws_cloudwatch_log_group" "all" {
  name              = "/${var.name}/all"
  retention_in_days = 14
}
