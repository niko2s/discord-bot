resource "aws_secretsmanager_secret" "bot" {
  name                    = "${var.name}/runtime"
  description             = "Runtime secrets (DISCORD_TOKEN, OPENAI_*, URBAN_KEY, ...)."
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret" "nordvpn" {
  name                    = "${var.name}/nordvpn"
  description             = "NordVPN OpenVPN service credentials for the Lavalink VPN."
  recovery_window_in_days = 0
}
