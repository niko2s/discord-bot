#!/bin/bash
set -eux

dnf update -y
dnf install -y docker amazon-ecr-credential-helper amazon-ssm-agent

systemctl enable --now amazon-ssm-agent

# Send all container logs to CloudWatch by default (must be set before Docker starts).
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<JSON
{
  "log-driver": "awslogs",
  "log-opts": {
    "awslogs-region": "${region}",
    "awslogs-group": "${log_group}",
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

# ECR credential helper for ec2-user.
mkdir -p /home/ec2-user/.docker
cat > /home/ec2-user/.docker/config.json <<DOCKER
{ "credsStore": "ecr-login" }
DOCKER

# Runtime env.
cat > /home/ec2-user/.bot.env <<ENV
BOT_IMAGE=${bot_image}
BOT_SECRET_ID=${bot_secret_id}
AWS_REGION=${region}
ENV

# Compose file — bot image pulled from ECR, env from .bot.env.
mkdir -p /home/ec2-user/bot
cat > /home/ec2-user/bot/docker-compose.yml <<'COMPOSE'
services:
  bot:
    image: $${BOT_IMAGE}
    restart: unless-stopped
    env_file:
      - .env
COMPOSE

ln -sf /home/ec2-user/.bot.env /home/ec2-user/bot/.env
chown -R ec2-user:ec2-user /home/ec2-user/.bot.env /home/ec2-user/.docker /home/ec2-user/bot
