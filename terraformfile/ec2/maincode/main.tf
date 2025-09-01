data "template_file" "init" {
    template = file("${path.module}/userdata.sh")
}

resource "aws_instance" "ec2" {
    ami           = var.ec2_ami
    ebs_optimized = var.ebs_optimized
    instance_type = var.ec2_type
    user_data     = base64encode(data.template_file.init.rendered)
    iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name
    associate_public_ip_address = false
    
    tags = {
      "Name" = format("%s",var.ec2_name)
    }


    subnet_id = local.subnet_id
    vpc_security_group_ids = [aws_security_group.ec2_sg.id]

root_block_device {
  volume_size = var.vol1_root_size
  volume_type = var.vol1_volume_type
  delete_on_termination = var.vol1_delete_on_termination
}

ebs_block_device {
  device_name = "/dev/sdh"
  volume_size = var.ec2_ebs2_data_size
  volume_type = "gp2"
}

}

output "instance_id" {
  value = aws_instance.ec2.id
}

output "instance_ip" {
  value = aws_instance.ec2.private_ip
}