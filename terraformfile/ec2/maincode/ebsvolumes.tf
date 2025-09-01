# Create the EBS volume for root
resource "aws_ebs_volume" "ec2_ebs_root" {
  availability_zone = var.ec2_availabilityzone
  size              = var.vol1_root_size
  type              = var.vol1_volume_type
  tags = {
    Name        = "${var.ec2_name}-root-volume"
    Environment = var.env
  }
}

# Create the EBS volume for data
resource "aws_ebs_volume" "ec2_ebs_data" {
  availability_zone = var.ec2_availabilityzone
  size              = var.ec2_ebs2_data_size
  type              = "gp2"
  tags = {
    Name        = "${var.ec2_name}-data-volume"
    Environment = var.env
  }
}
