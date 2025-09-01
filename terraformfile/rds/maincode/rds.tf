variable "db_identifier" {
  type        = string
  description = "The name of the RDS instance."
}

variable "db_engine" {
  type        = string
  description = "The database engine to use."
  default     = "mysql"
}

variable "db_username" {
  type        = string
  description = "The username for the database."
}

variable "db_password" {
  type        = string
  description = "The password for the database."
  sensitive   = true
}

variable "db_engine_version" {
  type        = string
  description = "The version of the database engine."
}

variable "db_instance_class" {
  type        = string
  description = "The instance type of the RDS instance."
}

variable "allocated_storage" {
  type        = number
  description = "The amount of allocated storage in GB."
}

variable "db_publicly_accessible" {
  type        = bool
  description = "Specifies if the DB instance is publicly accessible."
  default     = false
}

resource "aws_db_instance" "rds_instance" {
  identifier           = var.db_identifier
  engine               = var.db_engine
  engine_version       = var.db_engine_version
  instance_class       = var.db_instance_class
  allocated_storage    = var.allocated_storage
  username             = var.db_username
  password             = var.db_password
  skip_final_snapshot  = true
  publicly_accessible = var.db_publicly_accessible

  db_subnet_group_name = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  tags = {
    Name = var.db_identifier
  }
}

output "db_identifier" {
  value = aws_db_instance.rds_instance.identifier
}

output "db_instance_address" {
  value = aws_db_instance.rds_instance.address
}
