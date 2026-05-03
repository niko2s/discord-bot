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

# ECR credential helper for ec2-user (so `docker pull` works without explicit login).
mkdir -p /home/ec2-user/.docker
cat > /home/ec2-user/.docker/config.json <<DOCKER
{ "credsStore": "ecr-login" }
DOCKER
chown -R ec2-user:ec2-user /home/ec2-user/.docker

# Compose substitution-time env (BOT_IMAGE, BOT_SECRET_ID, AWS_REGION).
# Lives outside the repo so `git pull` doesn't clobber it.
cat > /home/ec2-user/.bot.env <<ENV
BOT_IMAGE=${bot_image}
BOT_SECRET_ID=${bot_secret_id}
AWS_REGION=${region}
ENV
chown ec2-user:ec2-user /home/ec2-user/.bot.env

sudo -u ec2-user git clone ${repo_url} /home/ec2-user/bot
ln -sf /home/ec2-user/.bot.env /home/ec2-user/bot/.env
