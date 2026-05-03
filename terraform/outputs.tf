output "instance_id" {
  description = "EC2 instance ID — set as the EC2_INSTANCE_ID GitHub Actions secret."
  value       = aws_instance.bot.id
}

output "public_ip" {
  description = "Public IPv4 of the bot host (for occasional manual SSM sessions)."
  value       = aws_instance.bot.public_ip
}

output "ecr_repository_url" {
  description = "ECR repository URL — set as the ECR_REPOSITORY GitHub Actions variable (just the path, e.g. discord-bot/bot)."
  value       = aws_ecr_repository.bot.repository_url
}

output "ecr_repository_name" {
  description = "Repository name (without the registry host), used by the deploy workflow."
  value       = aws_ecr_repository.bot.name
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret. Populate its value via `aws secretsmanager put-secret-value` (see DEPLOY.md)."
  value       = aws_secretsmanager_secret.bot.arn
}

output "log_group" {
  description = "CloudWatch log group containing all container logs."
  value       = aws_cloudwatch_log_group.all.name
}
