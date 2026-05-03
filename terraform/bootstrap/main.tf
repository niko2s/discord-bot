# One-time bootstrap: creates the S3 bucket and DynamoDB table that hold the
# remote state for the main module. Apply this once with LOCAL state, then never
# again. The main module's `backend "s3"` config points at what this creates.

terraform {
  required_version = ">= 1.6"
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

variable "lock_table" {
  type    = string
  default = "discord-bot-tflock"
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

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "lock" {
  name         = var.lock_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}

output "backend_config" {
  description = "Paste these values into terraform/backend.hcl (or use -backend-config flags)."
  value = <<-EOT
    bucket         = "${aws_s3_bucket.state.id}"
    key            = "discord-bot/terraform.tfstate"
    region         = "${var.region}"
    dynamodb_table = "${aws_dynamodb_table.lock.id}"
    encrypt        = true
  EOT
}
