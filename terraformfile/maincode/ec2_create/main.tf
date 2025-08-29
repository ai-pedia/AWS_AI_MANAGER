module "my_ec2" {
    source          = "../"
    awsAccountId    = var.awsAccountId
    #region          = var.region
    ##environment     = var.env
    #subnetname      = "app-ec2-1"
    ec2_availabilityzone = "us-east-1a"
    ec2_name        = var.ec2_name
    ec2_type        = "t2.micro"
    vol1_root_size  = var.vol1_root_size
    vol1_volume_type = var.vol1_volume_type
    #ec2_ebs2_data_type = "gp2"
    ec2_ebs2_data_size = var.ec2_ebs2_data_size
    ec2_ami           = var.ec2_ami
    #security_group    = ["default"]
}