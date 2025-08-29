from python_terraform import Terraform, IsNotFlagged
import os
import boto3
import re

def _run_terraform_apply(resource_dir: str, tfvars_path: str):
    terraform = Terraform(working_dir=resource_dir)
    print(f"Terraform initializing in {resource_dir}...")
    return_code, stdout, stderr = terraform.init()
    if return_code != 0:
        raise Exception(f"Terraform init failed: {stderr}")
    print("Terraform init complete. Applying changes...")
    return_code, stdout, stderr = terraform.apply(
        var_file=tfvars_path, 
        skip_plan=True, 
        auto_approve=True
    )
    if return_code != 0:
        raise Exception(f"Terraform apply failed: {stderr}\nStdout: {stdout}")
    print("Terraform apply complete.")
    return stdout

def _run_terraform_destroy(resource_dir: str, tfvars_path: str):
    terraform = Terraform(working_dir=resource_dir)
    print(f"Terraform initializing in {resource_dir}...")
    return_code, stdout, stderr = terraform.init()
    if return_code != 0:
        raise Exception(f"Terraform init failed: {stderr}")
    print("Terraform init complete. Destroying resources...")
    return_code, stdout, stderr = terraform.destroy(
        var_file=tfvars_path, 
        force=IsNotFlagged,
        auto_approve=True
    )
    if return_code != 0:
        raise Exception(f"Terraform destroy failed: {stderr}\nStdout: {stdout}")
    
    if os.path.exists(tfvars_path):
        os.remove(tfvars_path)
        
    print("Resource destroyed successfully.")
    return "Resource destroyed successfully."

def _validate_ami_id(ami_id: str) -> bool:
    # Basic regex for AMI ID format: ami- followed by 8 or 17 alphanumeric characters
    return bool(re.fullmatch(r'^ami-[0-9a-fA-F]{8}([0-9a-fA-F]{9})?$', ami_id))

def _validate_instance_type(instance_type: str) -> bool:
    # This would ideally involve calling AWS API (e.g., ec2.describe_instance_type_offerings)
    # For now, a simple check for common patterns or a predefined list.
    # A more robust solution would cache valid instance types.
    common_instance_types = ["t2.micro", "t2.small", "t2.medium", "t3.micro", "m5.large", "c5.xlarge"]
    return instance_type in common_instance_types

def _validate_volume_type(volume_type: str) -> bool:
    # Valid EBS volume types
    valid_volume_types = ["gp2", "gp3", "io1", "io2", "st1", "sc1", "standard"]
    return volume_type in valid_volume_types

def create_ec2(ec2_name: str,vol1_root_size: int,vol1_volume_type: str,ec2_ebs2_data_size: int,ec2_ami: str, ec2_availabilityzone: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2'))
    tfvars_path = os.path.join(resource_dir, f'terraform_ec2_{ec2_name}.tfvars')
    with open(tfvars_path,'w') as f:
        f.write(f'ec2_name = "{ec2_name}"\n')
        f.write(f'vol1_root_size = {vol1_root_size}\n')
        f.write(f'vol1_volume_type = "{vol1_volume_type}"\n')
        f.write(f'ec2_ebs2_data_size = {ec2_ebs2_data_size}\n')
        f.write(f'ec2_ami = "{ec2_ami}"\n')
        f.write(f'ec2_availabilityzone = "{ec2_availabilityzone}"\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def update_ec2_volume_size(instance_id: str, new_volume_size: int):
    details = get_ec2_details(instance_id)
    ec2_name = details['ec2_name']
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2'))
    tfvars_path = os.path.join(resource_dir, f'terraform_ec2_{ec2_name}.tfvars')

    # Update the volume size in the tfvars file
    with open(tfvars_path, 'w') as f:
        f.write(f'ec2_name = "{details['ec2_name']}"\n')
        f.write(f'vol1_root_size = {new_volume_size}\n') # Updated size
        f.write(f'vol1_volume_type = "{details['vol1_volume_type']}"\n')
        f.write(f'ec2_ebs2_data_size = {details['ec2_ebs2_data_size']}\n')
        f.write(f'ec2_ami = "{details['ec2_ami']}"\n')
        f.write(f'ec2_availabilityzone = "{details['ec2_availabilityzone']}"\n')
    
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_s3_bucket(bucket_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 's3'))
    tfvars_path = os.path.join(resource_dir, f'terraform_s3_{bucket_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'bucket_name = "{bucket_name}"\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_rds(db_identifier: str, db_engine: str, db_engine_version: str, db_instance_class: str, allocated_storage: int, db_username: str, db_password: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'rds'))
    tfvars_path = os.path.join(resource_dir, f'terraform_rds_{db_identifier}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'db_identifier = "{db_identifier}"\n')
        f.write(f'db_engine = "{db_engine}"\n')
        f.write(f'db_engine_version = "{db_engine_version}"\n')
        f.write(f'db_instance_class = "{db_instance_class}"\n')
        f.write(f'allocated_storage = {allocated_storage}\n')
        f.write(f'db_username = "{db_username}"\n')
        f.write(f'db_password = "{db_password}"\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_dynamodb(table_name: str, hash_key_name: str, hash_key_type: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'dynamodb'))
    tfvars_path = os.path.join(resource_dir, f'terraform_dynamodb_{table_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'dynamodb_table_name = "{table_name}"\n')
        f.write(f'dynamodb_hash_key_name = "{hash_key_name}"\n')
        f.write(f'dynamodb_hash_key_type = "{hash_key_type}"\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_iam_user(user_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_user_{user_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_user_name = "{user_name}"\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_iam_role(role_name: str):
    print(f"DEBUG: create_iam_role - role_name: '{role_name}'") # DEBUG PRINT
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_role_{role_name}.tfvars')
    print(f"DEBUG: create_iam_role - tfvars_path: '{tfvars_path}'") # DEBUG PRINT
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_role_name = "{role_name}"\n')
    # Read back the content to verify
    with open(tfvars_path, 'r') as f:
        content = f.read()
        print(f"DEBUG: create_iam_role - tfvars content: '{content}'") # DEBUG PRINT
    return _run_terraform_apply(resource_dir, tfvars_path)

def create_iam_policy(policy_name: str, policy_description: str, policy_document: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_policy_{policy_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_policy_name = "{policy_name}"\n')
        f.write(f'iam_policy_description = "{policy_description}"\n')
        f.write(f'iam_policy_document = <<-EOT\n')
        f.write(f'{policy_document}\n')
        f.write(f'EOT\n')
    return _run_terraform_apply(resource_dir, tfvars_path)

def get_ec2_details(instance_id: str):
    ec2 = boto3.client('ec2')
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if not response['Reservations'] or not response['Reservations'][0]['Instances']:
            raise Exception("Instance not found")
        
        instance = response['Reservations'][0]['Instances'][0]
        
        details = {
            'ec2_ami': instance['ImageId'],
            'ec2_availabilityzone': instance['Placement']['AvailabilityZone'],
            'ec2_name': '',
            'vol1_root_size': 0,
            'vol1_volume_type': '',
            'ec2_ebs2_data_size': 0
        }

        for tag in instance.get('Tags', []):
            if tag['Key'] == 'Name':
                details['ec2_name'] = tag['Value']
                break

        for bd in instance.get('BlockDeviceMappings', []):
            if bd.get('DeviceName') == instance.get('RootDeviceName'):
                volume_id = bd['Ebs']['VolumeId']
                vol_response = ec2.describe_volumes(VolumeIds=[volume_id])
                if vol_response['Volumes']:
                    details['vol1_root_size'] = vol_response['Volumes'][0]['Size']
                    details['vol1_volume_type'] = vol_response['Volumes'][0]['VolumeType']
            else:
                volume_id = bd['Ebs']['VolumeId']
                vol_response = ec2.describe_volumes(VolumeIds=[volume_id])
                if vol_response['Volumes']:
                    details['ec2_ebs2_data_size'] = vol_response['Volumes'][0]['Size']

        return details
    except Exception as e:
        raise Exception(f"Failed to get instance details: {e}")

def destroy_ec2(instance_id: str):
    details = get_ec2_details(instance_id)
    ec2_name = details['ec2_name']
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2'))
    tfvars_path = os.path.join(resource_dir, f'terraform_ec2_{ec2_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def destroy_s3_bucket(bucket_name: str):
    s3 = boto3.client('s3')
    try:
        # List and delete all object versions
        paginator = s3.get_paginator('list_object_versions')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Versions' in page:
                for obj_version in page['Versions']:
                    s3.delete_object(Bucket=bucket_name, Key=obj_version['Key'], VersionId=obj_version['VersionId'])
            if 'DeleteMarkers' in page:
                for del_marker in page['DeleteMarkers']:
                    s3.delete_object(Bucket=bucket_name, Key=del_marker['Key'], VersionId=del_marker['VersionId'])
        
        # List and delete all objects (for non-versioned buckets or after versions are cleared)
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})

    except Exception as e:
        # If the bucket doesn't exist or other error during emptying, proceed to destroy via terraform
        # as terraform destroy will handle non-existent resources gracefully.
        print(f"Warning: Could not empty S3 bucket {bucket_name} using boto3: {e}. Attempting Terraform destroy anyway.")

    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 's3'))
    tfvars_path = os.path.join(resource_dir, f'terraform_s3_{bucket_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def destroy_rds(db_identifier: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'rds'))
    tfvars_path = os.path.join(resource_dir, f'terraform_rds_{db_identifier}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def destroy_dynamodb(table_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'dynamodb'))
    tfvars_path = os.path.join(resource_dir, f'terraform_dynamodb_{table_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)



def destroy_iam_user(user_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_user_{user_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def destroy_iam_role(role_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_role_{role_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def destroy_iam_policy(policy_name: str):
    resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    tfvars_path = os.path.join(resource_dir, f'terraform_iam_policy_{policy_name}.tfvars')
    return _run_terraform_destroy(resource_dir, tfvars_path)

def list_ec2():
    ec2 = boto3.client('ec2')
    instances = []
    try:
        response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'pending']}])
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_name = ''
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
                instances.append({'InstanceId': instance_id, 'Name': instance_name, 'State': instance['State']['Name']})
        return instances
    except Exception as e:
        raise Exception(f"Failed to list EC2 instances: {e}")

def list_s3_buckets():
    s3 = boto3.client('s3')
    buckets = []
    try:
        response = s3.list_buckets()
        for bucket in response['Buckets']:
            buckets.append({'Name': bucket['Name']})
        return buckets
    except Exception as e:
        raise Exception(f"Failed to list S3 buckets: {e}")

def list_rds_instances():
    rds = boto3.client('rds')
    instances = []
    try:
        response = rds.describe_db_instances()
        for instance in response['DBInstances']:
            instances.append({'DBInstanceIdentifier': instance['DBInstanceIdentifier'], 'DBInstanceStatus': instance['DBInstanceStatus']})
        return instances
    except Exception as e:
        raise Exception(f"Failed to list RDS instances: {e}")

def get_supported_rds_engine_versions(engine: str, instance_class: str) -> list[str]:
    rds = boto3.client('rds')
    versions = []
    try:
        paginator = rds.get_paginator('describe_db_engine_versions')
        for page in paginator.paginate(Engine=engine, DBInstanceClass=instance_class):
            for db_engine_version in page['DBEngineVersions']:
                versions.append(db_engine_version['EngineVersion'])
        return sorted(list(set(versions)), reverse=True) # Return unique, sorted, newest first
    except Exception as e:
        # Log the error but don't raise, so the conversation can continue with a fallback message
        print(f"Error fetching supported RDS engine versions for {engine}/{instance_class}: {e}")
        return []

def list_dynamodb_tables():
    dynamodb = boto3.client('dynamodb')
    tables = []
    try:
        response = dynamodb.list_tables()
        for table_name in response['TableNames']:
            tables.append({'TableName': table_name})
        return tables
    except Exception as e:
        raise Exception(f"Failed to list DynamoDB tables: {e}")

def list_iam_users():
    iam = boto3.client('iam')
    users = []
    try:
        response = iam.list_users()
        for user in response['Users']:
            users.append({'UserName': user['UserName']})
        return users
    except Exception as e:
        raise Exception(f"Failed to list IAM users: {e}")

def list_iam_roles():
    iam = boto3.client('iam')
    roles = []
    try:
        response = iam.list_roles()
        for role in response['Roles']:
            roles.append({'RoleName': role['RoleName']})
        return roles
    except Exception as e:
        raise Exception(f"Failed to list IAM roles: {e}")

def list_iam_policies():
    iam = boto3.client('iam')
    policies = []
    try:
        response = iam.list_policies(Scope='Local') # List customer managed policies
        for policy in response['Policies']:
            policies.append({'PolicyName': policy['PolicyName'], 'Arn': policy['Arn']})
        return policies
    except Exception as e:
        raise Exception(f"Failed to list IAM policies: {e}")
