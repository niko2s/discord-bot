data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_iam_openid_connect_provider" "github" {
  arn = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions" {
  name = "github-actions-discord-bot"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:niko2s/discord-bot:environment:production"
        }
      }
    }]
  })

  tags = {
    ManagedBy = "Terraform"
    Project   = var.name
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "${var.name}-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "PushBotImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = aws_ecr_repository.bot.arn
      },
      {
        Sid    = "DeployToBotInstance"
        Effect = "Allow"
        Action = "ssm:SendCommand"
        Resource = [
          aws_instance.bot.arn,
          "arn:${data.aws_partition.current.partition}:ssm:${var.region}::document/AWS-RunShellScript",
        ]
      },
      {
        Sid      = "ReadDeploymentResult"
        Effect   = "Allow"
        Action   = "ssm:GetCommandInvocation"
        Resource = "*"
      },
    ]
  })
}

# This role uses only the scoped inline policy above. Keeping attachments
# exclusive prevents broad managed policies from being added out of band.
resource "aws_iam_role_policy_attachments_exclusive" "github_actions" {
  role_name   = aws_iam_role.github_actions.name
  policy_arns = []
}

import {
  to = aws_iam_role.github_actions
  id = "github-actions-discord-bot"
}
