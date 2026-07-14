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
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.bot.name
  vpc_security_group_ids = [aws_security_group.bot.id]

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    region             = var.region
    log_group          = aws_cloudwatch_log_group.all.name
    bot_image          = "${aws_ecr_repository.bot.repository_url}:latest"
    bot_secret_id      = aws_secretsmanager_secret.bot.name
    nordvpn_secret_id  = aws_secretsmanager_secret.nordvpn.name
    application_config = file("${path.module}/../application.yaml")
  })

  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
    http_tokens                 = "required"
  }

  root_block_device {
    volume_size = 30
  }

  tags = {
    Name = var.name
  }
}
