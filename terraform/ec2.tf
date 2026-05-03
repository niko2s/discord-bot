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
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.bot.name
  vpc_security_group_ids = [aws_security_group.bot.id]

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    region        = var.region
    log_group     = aws_cloudwatch_log_group.all.name
    bot_image     = "${aws_ecr_repository.bot.repository_url}:latest"
    bot_secret_id = aws_secretsmanager_secret.bot.name
    repo_url      = var.repo_url
  })

  tags = {
    Name = var.name
  }
}
