resource "aws_subnet" "ec2_subnet" {
  cidr_block = var.subnet_cidr
  vpc_id     = aws_vpc.ec2_vpc.id
  availability_zone = var.ec2_availabilityzone
}

resource "aws_vpc" "ec2_vpc" {
  cidr_block = var.vpc_cidr
}

resource "aws_security_group" "ec2_sg" {
  name        = "ec2_sg"
  description = "Security group for EC2 instance"
  vpc_id      = aws_vpc.ec2_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_network_interface" "ec2_nic" {
  subnet_id       = aws_subnet.ec2_subnet.id
  private_ip      = "10.0.1.100"
  security_groups = [aws_security_group.ec2_sg.id]
}