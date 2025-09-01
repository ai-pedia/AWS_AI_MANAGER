data "aws_iam_policy_document" "instance-assume-role-policy" {
  statement {
    actions = [ "sts:AssumeRole" ]
    principals {
      type        = "Service"
      identifiers = [ var.service_identifiers ]
    }
  }
}

resource "aws_iam_role" "iam_role" {
  assume_role_policy = coalesce(var.assume_role_policy, data.aws_iam_policy_document.instance-assume-role-policy.json)
  name               = "travrol-${var.ec2_name}"
  description        = "ec2 instance profile"
  force_detach_policies = var.force_detach_polices
}

resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = aws_iam_role.iam_role.name
  role = aws_iam_role.iam_role.id
}