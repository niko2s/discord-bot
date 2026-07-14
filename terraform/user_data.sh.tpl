#!/bin/bash
set -eux

dnf update -y
dnf install -y docker amazon-ecr-credential-helper amazon-ssm-agent jq

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

# Resolve NordVPN credentials at runtime. The secret value is never stored in
# Terraform state or EC2 user data, and xtrace is intentionally not enabled here.
cat > /usr/local/bin/render-nordvpn-env <<'SCRIPT'
#!/bin/bash
set -euo pipefail

tmp_file="$(mktemp /run/discord-bot/nordvpn.env.XXXXXX)"
trap 'rm -f "$tmp_file"' EXIT

aws secretsmanager get-secret-value \
  --region "$AWS_REGION" \
  --secret-id "$NORDVPN_SECRET_ID" \
  --query SecretString \
  --output text \
  | jq -er '
      if (.OPENVPN_USER | type) == "string" and (.OPENVPN_USER | length) > 0
         and (.OPENVPN_PASSWORD | type) == "string" and (.OPENVPN_PASSWORD | length) > 0
      then "OPENVPN_USER=\(.OPENVPN_USER | @json)\nOPENVPN_PASSWORD=\(.OPENVPN_PASSWORD | @json)"
      else error("NordVPN secret must contain OPENVPN_USER and OPENVPN_PASSWORD")
      end
    ' > "$tmp_file"

chmod 600 "$tmp_file"
mv "$tmp_file" /run/discord-bot/nordvpn.env
trap - EXIT
SCRIPT
chmod 755 /usr/local/bin/render-nordvpn-env

# Production Compose stack. Only Lavalink shares the VPN network namespace;
# the bot, SSM, ECR and CloudWatch keep the instance's normal network route.
mkdir -p /home/ec2-user/bot
cat > /home/ec2-user/bot/docker-compose.yml <<'COMPOSE'
services:
  vpn:
    image: qmcgaw/gluetun:v3.41.1
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    env_file:
      - /run/discord-bot/nordvpn.env
    environment:
      VPN_SERVICE_PROVIDER: nordvpn
      VPN_TYPE: openvpn
      SERVER_COUNTRIES: Germany
      FIREWALL_INPUT_PORTS: "2333"
    expose:
      - "2333"
    networks:
      - bot-net

  lavalink-init:
    image: ghcr.io/lavalink-devs/lavalink:4
    user: "0:0"
    entrypoint: ["/bin/sh", "-c"]
    command: ["chown -R 322:322 /plugins /logs"]
    volumes:
      - lavalink-plugins:/plugins
      - lavalink-logs:/logs

  lavalink:
    image: ghcr.io/lavalink-devs/lavalink:4
    restart: unless-stopped
    network_mode: service:vpn
    depends_on:
      vpn:
        condition: service_healthy
      lavalink-init:
        condition: service_completed_successfully
    environment:
      _JAVA_OPTIONS: "-Djava.net.preferIPv4Stack=true"
    volumes:
      - ./application.yaml:/opt/Lavalink/application.yml:ro
      - lavalink-plugins:/opt/Lavalink/plugins
      - lavalink-logs:/opt/Lavalink/logs
    healthcheck:
      test: ["CMD", "bash", "-c", "echo > /dev/tcp/127.0.0.1/2333"]
      interval: 10s
      timeout: 3s
      retries: 12

  bot:
    image: $${BOT_IMAGE}
    restart: unless-stopped
    env_file:
      - .env
    environment:
      LAVALINK_HOST: vpn
      LAVALINK_PORT: "2333"
      LAVALINK_PASSWORD: "youshallnotpass"
    depends_on:
      lavalink:
        condition: service_healthy
    networks:
      - bot-net

networks:
  bot-net:

volumes:
  lavalink-plugins:
  lavalink-logs:
COMPOSE

cat > /home/ec2-user/bot/application.yaml <<'LAVALINK_CONFIG'
${application_config}
LAVALINK_CONFIG

ln -sf /home/ec2-user/.bot.env /home/ec2-user/bot/.env
chown -R ec2-user:ec2-user /home/ec2-user/.bot.env /home/ec2-user/.docker /home/ec2-user/bot
chmod 600 /home/ec2-user/.bot.env

# Start the stack after rendering the VPN credentials. If the secret has not
# been populated yet, systemd retries without exposing the credentials in logs.
cat > /etc/systemd/system/discord-bot-stack.service <<UNIT
[Unit]
Description=Discord bot, Lavalink and NordVPN containers
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ec2-user
Group=ec2-user
SupplementaryGroups=docker
RuntimeDirectory=discord-bot
RuntimeDirectoryMode=0700
Environment=AWS_REGION=${region}
Environment=NORDVPN_SECRET_ID=${nordvpn_secret_id}
ExecStartPre=/usr/local/bin/render-nordvpn-env
ExecStartPre=-/usr/bin/docker compose --project-directory /home/ec2-user/bot down --remove-orphans
ExecStart=/usr/bin/docker compose --project-directory /home/ec2-user/bot up -d
RemainAfterExit=yes
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable discord-bot-stack.service
# The NordVPN secret may be populated immediately after the first apply. The
# unit retries every 30 seconds, so an initially missing value is expected.
systemctl start discord-bot-stack.service || true
