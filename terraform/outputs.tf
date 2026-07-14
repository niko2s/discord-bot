output "instance_id" {
  description = "EC2 instance ID — set as the EC2_INSTANCE_ID GitHub Actions secret."
  value       = aws_instance.bot.id
}

output "public_ip" {
  description = "Public IPv4 of the bot host."
  value       = aws_instance.bot.public_ip
}

output "ecr_repository_url" {
  description = "ECR repository URL."
  value       = aws_ecr_repository.bot.repository_url
}

output "ecr_repository_name" {
  description = "ECR repository name (no registry host)."
  value       = aws_ecr_repository.bot.name
}

output "secret_arn" {
  description = "Secrets Manager secret ARN."
  value       = aws_secretsmanager_secret.bot.arn
}

output "nordvpn_secret_arn" {
  description = "NordVPN service-credentials secret ARN."
  value       = aws_secretsmanager_secret.nordvpn.arn
}

output "log_group" {
  description = "CloudWatch log group for container logs."
  value       = aws_cloudwatch_log_group.all.name
}
