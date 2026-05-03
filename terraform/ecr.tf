resource "aws_ecr_repository" "bot" {
  name                 = "${var.name}/bot"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true
}

resource "aws_ecr_lifecycle_policy" "bot" {
  repository = aws_ecr_repository.bot.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the most recent 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}
