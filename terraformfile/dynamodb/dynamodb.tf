variable "dynamodb_table_name" {
  type        = string
  description = "The name of the DynamoDB table."
}

variable "dynamodb_hash_key_name" {
  type        = string
  description = "The name of the hash key."
}

variable "dynamodb_hash_key_type" {
  type        = string
  description = "The type of the hash key (S for string, N for number, B for binary)."
  default     = "S"
}

resource "aws_dynamodb_table" "dynamodb_table" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = var.dynamodb_hash_key_name

  attribute {
    name = var.dynamodb_hash_key_name
    type = var.dynamodb_hash_key_type
  }

  tags = {
    Name = var.dynamodb_table_name
  }
}
