# --- Find Default VPC ---

data "aws_vpc" "default" {
  default = true
}

# --- Create VPC if Default is Not Found ---

resource "aws_vpc" "created" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "gemini-created-vpc-for-rds"
  }
}

locals {
  vpc_id = data.aws_vpc.default.id != null ? data.aws_vpc.default.id : aws_vpc.created[0].id
}

# --- Subnets ---

# Create at least two subnets in different AZs for the DB subnet group
resource "aws_subnet" "a" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  vpc_id     = local.vpc_id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a" # Example AZ, consider making this dynamic
  tags = {
    Name = "gemini-created-rds-subnet-a"
  }
}

resource "aws_subnet" "b" {
  count = data.aws_vpc.default.id == null ? 1 : 0
  vpc_id     = local.vpc_id
  cidr_block = "10.0.2.0/24"
  availability_zone = "us-east-1b" # Example AZ, consider making this dynamic
  tags = {
    Name = "gemini-created-rds-subnet-b"
  }
}

data "aws_subnets" "default_subnets" {
  count = data.aws_vpc.default.id != null ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

locals {
  subnet_ids = data.aws_vpc.default.id != null ? data.aws_subnets.default_subnets[0].ids : [aws_subnet.a[0].id, aws_subnet.b[0].id]
}

# --- DB Subnet Group ---

resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "rds-subnet-group-${var.db_identifier}"
  subnet_ids = local.subnet_ids

  tags = {
    Name = "RDS Subnet Group for ${var.db_identifier}"
  }
}

# --- Security Group ---

resource "aws_security_group" "rds_sg" {
  name        = "rds_sg_${var.db_identifier}"
  description = "Security group for RDS instance ${var.db_identifier}"
  vpc_id      = local.vpc_id

  # Allow inbound traffic on the database port (e.g., 5432 for PostgreSQL)
  # This should be locked down to specific IPs in a real environment
  ingress {
    from_port   = 0 # Allows all ports, for simplicity. Should be specific (e.g. 5432)
    to_port     = 0
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
