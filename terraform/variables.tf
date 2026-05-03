variable "region" {
  description = "AWS region. eu-central-1 is closest to Discord's Frankfurt voice servers."
  type        = string
  default     = "eu-central-1"
}

variable "name" {
  description = "Resource-name prefix used for SG, IAM, and instance tags."
  type        = string
  default     = "discord-bot"
}

variable "instance_type" {
  description = "EC2 instance type. t4g.small is enough for one bot + Lavalink."
  type        = string
  default     = "t4g.small"
}

variable "repo_url" {
  description = "Git URL the EC2 box clones at first boot (e.g. https://github.com/you/discord-bot.git)."
  type        = string
}
