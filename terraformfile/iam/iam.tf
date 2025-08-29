variable "iam_user_name" {
  type        = string
  description = "The name of the IAM user."
  default     = ""
}

variable "iam_role_name" {
  type        = string
  description = "The name of the IAM role."
  default     = ""
}

variable "iam_policy_name" {
  type        = string
  description = "The name of the IAM policy."
  default     = ""
}

variable "iam_policy_description" {
  type        = string
  description = "The description of the IAM policy."
  default     = "A sample IAM policy."
}

variable "iam_policy_document" {
  type        = string
  description = "The policy document."
  default     = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:ListBucket"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_user" "iam_user" {
  count = var.iam_user_name != "" ? 1 : 0
  name  = var.iam_user_name
}

resource "aws_iam_role" "iam_role" {
  count = var.iam_role_name != "" ? 1 : 0
  name  = var.iam_role_name
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_policy" "iam_policy" {
  count       = var.iam_policy_name != "" ? 1 : 0
  name        = var.iam_policy_name
  description = var.iam_policy_description
  policy      = var.iam_policy_document
}