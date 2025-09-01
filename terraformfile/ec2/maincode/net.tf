# --- Find Default VPC ---

data "aws_vpc" "default" {
  default = true
}

# --- Create VPC if Default is Not Found ---

resource "aws_vpc" "created" {
  # Only create this VPC if the data source found nothing
  count = data.aws_vpc.default.id == null ? 1 : 0

  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "gemini-created-vpc"
  }
}

# Use the ID from the default VPC if it exists, otherwise use the newly created one.
locals {
  vpc_id = data.aws_vpc.default.id != null ? data.aws_vpc.default.id : aws_vpc.created[0].id
}

# --- Subnets ---

resource "aws_subnet" "main" {
  # Only create this if we also created a VPC
  count = data.aws_vpc.default.id == null ? 1 : 0

  vpc_id     = local.vpc_id
  cidr_block = "10.0.1.0/24"
  availability_zone = var.ec2_availabilityzone

  tags = {
    Name = "gemini-created-subnet"
  }
}

# Use the first available subnet from the default VPC, or the newly created one.
data "aws_subnets" "default_subnets" {
  # Only run this if the default VPC exists
  count = data.aws_vpc.default.id != null ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
  filter {
    name   = "availability-zone"
    values = [var.ec2_availabilityzone]
  }
}

locals {
  subnet_id = data.aws_vpc.default.id != null ? data.aws_subnets.default_subnets[0].ids[0] : aws_subnet.main[0].id
}

# --- Internet Gateway for Created VPC ---

resource "aws_internet_gateway" "gw" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  vpc_id = local.vpc_id

  tags = {
    Name = "gemini-igw"
  }
}

resource "aws_route_table" "rt" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  vpc_id = local.vpc_id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw[0].id
  }

  tags = {
    Name = "gemini-route-table"
  }
}

resource "aws_route_table_association" "a" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  subnet_id      = local.subnet_id
  route_table_id = aws_route_table.rt[0].id
}

# --- Security Group (Common) ---

resource "aws_security_group" "ec2_sg" {
  name        = "ec2_sg_${var.ec2_name}"
  description = "Security group for EC2 instance ${var.ec2_name}"
  vpc_id      = local.vpc_id

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