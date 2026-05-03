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

# ---------------------------------------------------------------- Networking

resource "aws_security_group" "bot" {
  name        = "${var.name}-sg"
  description = "Discord bot egress only"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------------------------------------------- ECR

resource "aws_ecr_repository" "bot" {
  name                 = "${var.name}/bot"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true
}

resource "aws_ecr_lifecycle_policy" "bot" {
  repository = aws_ecr_repository.bot.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the most recent 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------- Secrets

# The secret resource itself; populate the value out of band (DEPLOY.md).
resource "aws_secretsmanager_secret" "bot" {
  name                    = "${var.name}/runtime"
  description             = "Runtime secrets injected into the bot at startup (DISCORD_TOKEN, OPENAI_*, URBAN_KEY, ...)."
  recovery_window_in_days = 0
}

# ---------------------------------------------------------------- Logs

resource "aws_cloudwatch_log_group" "all" {
  name              = "/${var.name}/all"
  retention_in_days = 14
}

# ---------------------------------------------------------------- IAM

resource "aws_iam_role" "bot" {
  name = "${var.name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Session Manager / Run-Command access.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.bot.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Pull from ECR.
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.bot.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Read the runtime secret + write CloudWatch Logs.
resource "aws_iam_role_policy" "runtime" {
  name = "${var.name}-runtime"
  role = aws_iam_role.bot.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.bot.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.all.arn}:*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "bot" {
  name = "${var.name}-profile"
  role = aws_iam_role.bot.name
}

# ---------------------------------------------------------------- EC2

resource "aws_instance" "bot" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.bot.name
  vpc_security_group_ids = [aws_security_group.bot.id]

  user_data = <<-EOT
    #!/bin/bash
    set -eux

    dnf update -y
    dnf install -y docker git amazon-ecr-credential-helper

    # Send all container logs to CloudWatch by default.
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<JSON
    {
      "log-driver": "awslogs",
      "log-opts": {
        "awslogs-region": "${var.region}",
        "awslogs-group": "${aws_cloudwatch_log_group.all.name}",
        "awslogs-create-group": "false",
        "tag": "{{.Name}}"
      }
    }
    JSON

    systemctl enable --now docker
    usermod -aG docker ec2-user

    # Compose v2 plugin (ARM64 binary).
    mkdir -p /usr/libexec/docker/cli-plugins
    curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" \
      -o /usr/libexec/docker/cli-plugins/docker-compose
    chmod +x /usr/libexec/docker/cli-plugins/docker-compose

    # ECR credential helper for ec2-user (so `docker pull` works without explicit login).
    mkdir -p /home/ec2-user/.docker
    cat > /home/ec2-user/.docker/config.json <<DOCKER
    { "credsStore": "ecr-login" }
    DOCKER
    chown -R ec2-user:ec2-user /home/ec2-user/.docker

    # Compose substitution-time env (BOT_IMAGE, BOT_SECRET_ID, AWS_REGION).
    # Lives outside the repo so `git pull` doesn't clobber it.
    cat > /home/ec2-user/.bot.env <<ENV
    BOT_IMAGE=${aws_ecr_repository.bot.repository_url}:latest
    BOT_SECRET_ID=${aws_secretsmanager_secret.bot.name}
    AWS_REGION=${var.region}
    ENV
    chown ec2-user:ec2-user /home/ec2-user/.bot.env

    sudo -u ec2-user git clone ${var.repo_url} /home/ec2-user/bot
    ln -sf /home/ec2-user/.bot.env /home/ec2-user/bot/.env
  EOT

  tags = {
    Name = var.name
  }
}
