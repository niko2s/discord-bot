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

# Latest standard Amazon Linux 2023 ARM64 AMI. The public parameter avoids
# accidentally selecting an ECS-optimized image with a matching name.
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

resource "aws_cloudwatch_log_group" "all" {
  name              = "/${var.name}/all"
  retention_in_days = 14
}
