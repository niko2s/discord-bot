# One-time bootstrap: creates the S3 bucket that holds the remote state for the
# main module. Apply this once with local state, then never again.
# Native S3 locking (Terraform >= 1.10) means no DynamoDB table is needed.

terraform {
  required_version = ">= 1.15"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "state_bucket" {
  description = "S3 bucket name for Terraform state. Must be globally unique. Try discord-bot-tfstate-<your-aws-account-id>."
  type        = string
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

output "backend_config" {
  description = "Paste these values into terraform/backend.hcl (or use -backend-config flags)."
  value       = <<-EOT
    bucket       = "${aws_s3_bucket.state.id}"
    key          = "discord-bot/terraform.tfstate"
    region       = "${var.region}"
    use_lockfile = true
  EOT
}
