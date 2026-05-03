resource "aws_cloudwatch_log_group" "all" {
  name              = "/${var.name}/all"
  retention_in_days = 14
}
