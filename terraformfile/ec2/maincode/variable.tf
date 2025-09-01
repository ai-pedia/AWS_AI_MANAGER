# Input variables for the Terraform configuration

# EC2 instance settings
variable "ec2_name" {
  type        = string
  default     = "Test_Ec2"
  description = "Name of the EC2 instance"
}

variable "ec2_type" {
  type        = string
  default     = "t2.micro"
  description = "Type of the EC2 instance"
}

# Root volume settings
variable "vol1_root_size" {
  type        = number
  default     = 50
  description = "Root Volume size"
}

variable "vol1_volume_type" {
  type        = string
  default     = "gp2"
  description = "Type of the root volume"
}

variable "vol1_delete_on_termination" {
  type        = bool
  default     = true
  description = "Delete the root volume on termination"
}

# EBS volume settings
variable "ec2_ebs2_data_size" {
  type        = number
  default     = 100
  description = "EBS volume for data"
}

variable "ebs_optimized" {
  type        = bool
  default     = false
  description = "If true, the EBS volume will be optimized"
}

# Instance naming settings
variable "name_prefix" {
  type        = string
  default     = ""
  description = "Custom name prefix for the instance"
}

# Termination protection settings
variable "disable_api_termination" {
  type        = bool
  default     = false
  description = "If true, enables EC2 instance termination protection"
}

# Availability zone and region settings
variable "ec2_availabilityzone" {
  type        = string
  default     = ""
  description = "Availability zone for the EC2 instance"
}

variable "ec2_region" {
  type        = string
  default     = ""
  description = "Region for the EC2 instance"
}

# Environment settings
variable "ec2_env" {
  type        = string
  default     = ""
  description = "Environment for the EC2 instance"
}

# AMI settings
variable "ec2_ami" {
  type        = string
  default     = ""
  description = "AMI for the EC2 instance"
}

# IAM role settings
variable "service_identifiers" {
  type        = string
  default     = "ec2.amazonaws.com"
  description = "Service identifiers for the IAM role"
}

variable "force_detach_polices" {
  type        = bool
  default     = false
  description = "If true, forces detachment of policies"
}

variable "assume_role_policy" {
  type        = string
  default     = ""
  description = "Assume role policy for the IAM role"
}

# Other settings
variable "lob" {
  type        = string
  default     = "test"
  description = "Line of business"
}

variable "ec2_project" {
  type        = string
  default     = "my"
  description = "Project for the EC2 instance"
}

variable "ec2_role_arn" {
  type        = list(string)
  default     = []
  description = "IAM roles to be attached to the EC2 instance"
}

variable "ec2_pol_arn" {
  type        = list(string)
  default     = []
  description = "IAM policies to be attached to the EC2 instance"
}

variable "env" {
  type        = string
  default     = "dev"
  description = "Environment"
}

variable "awsAccountId" {
  type        = string
  default     = ""
  description = "AWS account ID"
}

variable "tfe_env" {
  type        = string
  default     = "dev"
  description = "Terraform environment"
}
variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "vpc_name" {
  type        = string
  default     = "my-vpc"
  description = "Name of the VPC"
}

variable "subnet_cidr" {
  type        = string
  default     = "10.0.1.0/24"
  description = "CIDR block for the subnet"
}
