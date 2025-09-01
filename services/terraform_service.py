from python_terraform import Terraform, IsNotFlagged
import os
import boto3
import re
import shutil
import json
import subprocess

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
    print("Terraform apply complete. Fetching outputs...")

    try:
        # Use subprocess to get the output as JSON
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=resource_dir,
            capture_output=True,
            text=True,
            check=True
        )
        stdout_str = result.stdout
        stderr_str = result.stderr

        if not stdout_str.strip():
            raise Exception(f"Terraform output is empty. No resources may have been created or there was an issue fetching outputs.\nRaw stderr: {stderr_str}")

        # Parse the JSON output into a Python dictionary
        parsed_output = json.loads(stdout_str)
        # Extract the 'value' from each output
        result = {key: data['value'] for key, data in parsed_output.items()}
        return result

    except subprocess.CalledProcessError as e:
        error_message = f"'terraform output -json' failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
        raise Exception(error_message)
    except json.JSONDecodeError as e:
        error_message = f"Failed to parse Terraform JSON output: {e}\nRaw stdout: {stdout_str}\nRaw stderr: {stderr_str}"
        raise Exception(error_message)
    except Exception as e: # Catch any other potential errors during processing
        error_message = f"Error processing Terraform output: {e}\nRaw stdout: {stdout_str}\nRaw stderr: {stderr_str}"
        raise Exception(error_message)

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
    
    # Clean up the instance directory
    if os.path.isdir(resource_dir):
        shutil.rmtree(resource_dir)
        
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

def create_ec2(ec2_name: str, ec2_type: str, vol1_root_size: int, vol1_volume_type: str, ec2_ebs2_data_size: int, ec2_ami: str, ec2_availabilityzone: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, ec2_name)
    
    # Create a new directory for the instance
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    # Copy template files to the new instance directory
    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_ec2_{ec2_name}.tfvars')
    with open(tfvars_path,'w') as f:
        f.write(f'ec2_name = "{ec2_name}"\n')
        f.write(f'ec2_type = "{ec2_type}"\n')
        f.write(f'vol1_root_size = {vol1_root_size}\n')
        f.write(f'vol1_volume_type = "{vol1_volume_type}"\n')
        f.write(f'ec2_ebs2_data_size = {ec2_ebs2_data_size}\n')
        f.write(f'ec2_ami = "{ec2_ami}"\n')
        f.write(f'ec2_availabilityzone = "{ec2_availabilityzone}"\n')
        
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_ec2 function
    instance_id = tf_outputs.get('instance_id')
    if not instance_id:
        raise Exception("Failed to get instance ID from Terraform output.")

    ec2 = boto3.client('ec2')
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instance = response['Reservations'][0]['Instances'][0]

    return {
        'InstanceId': instance_id,
        'Name': ec2_name,
        'State': instance['State']['Name'],
        'instance_ip': instance.get('PrivateIpAddress', 'N/A')
    }


def update_ec2_volume_size(instance_id: str, new_volume_size: int):
    details = get_ec2_details(instance_id)
    ec2_name = details['ec2_name']
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2', ec2_name))
    tfvars_path = os.path.join(instance_dir, f'terraform_ec2_{ec2_name}.tfvars')

    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot update instance '{ec2_name}'. Directory not found.")

    # Update the volume size in the tfvars file
    with open(tfvars_path, 'w') as f:
        f.write(f'ec2_name = "{details['ec2_name']}"\n')
        f.write(f'vol1_root_size = {new_volume_size}\n') # Updated size
        f.write(f'vol1_volume_type = "{details['vol1_volume_type']}"\n')
        f.write(f'ec2_ebs2_data_size = {details['ec2_ebs2_data_size']}\n')
        f.write(f'ec2_ami = "{details['ec2_ami']}"\n')
        f.write(f'ec2_availabilityzone = "{details['ec2_availabilityzone']}"\n')
    
    return _run_terraform_apply(instance_dir, tfvars_path)

def create_s3_bucket(bucket_name: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 's3'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, bucket_name)
    
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_s3_{bucket_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'bucket_name = "{bucket_name}"\n')
    
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_s3_buckets function
    return {
        'Name': tf_outputs.get('bucket_name', bucket_name) # Use output if available, else fallback to input
    }

def create_rds(db_identifier: str, db_engine: str, db_engine_version: str, db_instance_class: str, allocated_storage: int, db_username: str, db_password: str, db_publicly_accessible: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'rds'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, db_identifier)
    
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_rds_{db_identifier}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'db_identifier = "{db_identifier}"\n')
        f.write(f'db_engine = "{db_engine}"\n')
        f.write(f'db_engine_version = "{db_engine_version}"\n')
        f.write(f'db_instance_class = "{db_instance_class}"\n')
        f.write(f'allocated_storage = {allocated_storage}\n')
        f.write(f'db_username = "{db_username}"\n')
        f.write(f'db_password = "{db_password}"\n')
        f.write(f'db_publicly_accessible = {str(db_publicly_accessible.lower() == "yes").lower()}\n')
    
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_rds_instances function
    rds = boto3.client('rds')
    response = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)
    instance = response['DBInstances'][0]

    return {
        'DBInstanceIdentifier': instance['DBInstanceIdentifier'],
        'DBInstanceStatus': instance['DBInstanceStatus']
    }

def create_dynamodb(table_name: str, hash_key_name: str, hash_key_type: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'dynamodb'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, table_name)
    
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_dynamodb_{table_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'dynamodb_table_name = "{table_name}"\n')
        f.write(f'dynamodb_hash_key_name = "{hash_key_name}"\n')
        f.write(f'dynamodb_hash_key_type = "{hash_key_type}"\n')
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_dynamodb_tables function
    return {
        'TableName': tf_outputs.get('dynamodb_table_name', table_name) # Use output if available, else fallback to input
    }

def create_iam_user(user_name: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, f"user_{user_name}")
    
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
    
    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_iam_user_{user_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_user_name = "{user_name}"\n')
    
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_iam_users function
    result = {
        'UserName': tf_outputs.get('iam_user_name', user_name) # Use output if available, else fallback to input
    }
    return result

def create_iam_role(role_name: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, f"role_{role_name}")

    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)

    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)
            
    tfvars_path = os.path.join(instance_dir, f'terraform_iam_role_{role_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_role_name = "{role_name}"\n')
    
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_iam_roles function
    return {
        'RoleName': tf_outputs.get('iam_role_name', role_name) # Use output if available, else fallback to input
    }

def create_iam_policy(policy_name: str, policy_description: str, policy_document: str):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam'))
    template_dir = os.path.join(base_dir, 'maincode')
    instance_dir = os.path.join(base_dir, f"policy_{policy_name}")

    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)

    for item in os.listdir(template_dir):
        s = os.path.join(template_dir, item)
        d = os.path.join(instance_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=True, ignore=None)
        else:
            shutil.copy2(s, d)

    tfvars_path = os.path.join(instance_dir, f'terraform_iam_policy_{policy_name}.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'iam_policy_name = "{policy_name}"\n')
        f.write(f'iam_policy_description = "{policy_description}"\n')
        f.write(f'iam_policy_document = <<-EOT\n')
        f.write(f'{policy_document}\n')
        f.write(f'EOT\n')
    
    tf_outputs = _run_terraform_apply(instance_dir, tfvars_path)

    # Standardize the output to match the list_iam_policies function
    iam = boto3.client('iam')
    response = iam.list_policies(Scope='Local')
    policy_arn = None
    for policy in response['Policies']:
        if policy['PolicyName'] == policy_name:
            policy_arn = policy['Arn']
            break

    return {
        'PolicyName': tf_outputs.get('iam_policy_name', policy_name),
        'Arn': policy_arn if policy_arn else 'N/A'
    }

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
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'ec2', ec2_name))
    tfvars_path = os.path.join(instance_dir, f'terraform_ec2_{ec2_name}.tfvars')

    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy instance '{ec2_name}'. Directory not found.")

    return _run_terraform_destroy(instance_dir, tfvars_path)

def destroy_s3_bucket(bucket_name: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 's3', bucket_name))
    tfvars_path = os.path.join(instance_dir, f'terraform_s3_{bucket_name}.tfvars')

    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy S3 bucket '{bucket_name}'. Directory not found.")

    return _run_terraform_destroy(instance_dir, tfvars_path)

def destroy_rds(db_identifier: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'rds', db_identifier))
    tfvars_path = os.path.join(instance_dir, f'terraform_rds_{db_identifier}.tfvars')

    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy RDS instance '{db_identifier}'. Directory not found.")

    return _run_terraform_destroy(instance_dir, tfvars_path)

def destroy_dynamodb(table_name: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'dynamodb', table_name))
    tfvars_path = os.path.join(instance_dir, f'terraform_dynamodb_{table_name}.tfvars')

    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy DynamoDB table '{table_name}'. Directory not found.")

    return _run_terraform_destroy(instance_dir, tfvars_path)



def destroy_iam_user(user_name: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam', f"user_{user_name}"))
    tfvars_path = os.path.join(instance_dir, f'terraform_iam_user_{user_name}.tfvars')
    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy IAM User '{user_name}'. Directory not found.")
    return _run_terraform_destroy(instance_dir, tfvars_path)

def destroy_iam_role(role_name: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam', f"role_{role_name}"))
    tfvars_path = os.path.join(instance_dir, f'terraform_iam_role_{role_name}.tfvars')
    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy IAM Role '{role_name}'. Directory not found.")
    return _run_terraform_destroy(instance_dir, tfvars_path)

def destroy_iam_policy(policy_name: str):
    instance_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'terraformfile', 'iam', f"policy_{policy_name}"))
    tfvars_path = os.path.join(instance_dir, f'terraform_iam_policy_{policy_name}.tfvars')
    if not os.path.exists(instance_dir):
        raise Exception(f"Cannot destroy IAM Policy '{policy_name}'. Directory not found.")
    return _run_terraform_destroy(instance_dir, tfvars_path)

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
                instances.append({
                    'InstanceId': instance_id, 
                    'Name': instance_name, 
                    'State': instance['State']['Name'],
                    'instance_ip': instance.get('PublicIpAddress', 'N/A')
                })
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
