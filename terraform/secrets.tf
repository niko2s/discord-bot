# The secret resource itself; populate the value out of band (DEPLOY.md).
resource "aws_secretsmanager_secret" "bot" {
  name                    = "${var.name}/runtime"
  description             = "Runtime secrets injected into the bot at startup (DISCORD_TOKEN, OPENAI_*, URBAN_KEY, ...)."
  recovery_window_in_days = 0
}
