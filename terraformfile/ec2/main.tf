data "template_file" "init" {
    template = file("${path.module}/userdata.sh")
}

resource "aws_instance" "ec2" {
    ami           = var.ec2_ami
    ebs_optimized = var.ebs_optimized
    instance_type = var.ec2_type
    user_data     = base64encode(data.template_file.init.rendered)
    iam_instance_profile = aws_iam_role.iam_role.name
    volume_tags = {
      "Name" = format("%s%s","volume for",var.ec2_name)
    }
    tags = {
      "Name" = format("%s",var.ec2_name)
    }
lifecycle {
  ignore_changes = [ private_ip,vpc_security_group_ids,root_block_device,ebs_block_device ]
}

network_interface {
    network_interface_id = aws_network_interface.ec2_nic.id
    device_index = 0
}

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