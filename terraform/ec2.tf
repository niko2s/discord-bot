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
