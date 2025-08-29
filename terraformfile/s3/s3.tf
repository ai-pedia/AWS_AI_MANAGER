variable "bucket_name" {
  type        = string
  description = "The name of the S3 bucket."
}

resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.bucket_name

  tags = {
    Name = var.bucket_name
  }
}
