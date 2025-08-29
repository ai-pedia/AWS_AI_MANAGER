variable "awsAccountId" {
    default = ""
}

variable "ec2_region" {
    default = ""
}

variable "ec2_availabilityzone" {
    default = ""
}

variable "ec2_env" {
    default = "aws_dev"
}

variable "env" {
    default = "dev"
}

variable "tfe_env" {
    default = "dev"
}

variable "vol1_root_size" {
    default = "50"
}

variable "vol1_volume_type" {
    default = "gp2"
}

variable "ec2_ebs2_data_type" {
    default = "gp2"
}

variable "ec2_ebs2_data_size" {
    default = "50"
}

variable "ec2_name" {
    default = "ec2"
}

variable "ec2_ami" {
    default = ""
}



variable "subnetName" {
    default = "app-ec2-1"
}

