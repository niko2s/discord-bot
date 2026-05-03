resource "aws_secretsmanager_secret" "bot" {
  name                    = "${var.name}/runtime"
  description             = "Runtime secrets (DISCORD_TOKEN, OPENAI_*, URBAN_KEY, ...)."
  recovery_window_in_days = 0
}
