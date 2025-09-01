import streamlit as st
import re
import traceback
import boto3
import json
from services import terraform_service
from services.terraform_service import _validate_ami_id, _validate_instance_type, _validate_volume_type
from utils.ai_client import send_to_perplexity

# --- Parameter Definitions for Resource Creation ---
RESOURCE_PARAMS = {
    "ec2": [
        {"name": "ec2_availabilityzone", "prompt": "What is the Availability Zone for your EC2 instance? (e.g., us-east-1a)"},
        {"name": "ec2_name", "prompt": "What would you like to name your EC2 instance?"},
        {"name": "ec2_ami", "prompt": "What is the AMI ID? (e.g., ami-0abcdef1234567890)"},
        {"name": "ec2_type", "prompt": "What is the Instance Type? (e.g., t2.micro, m5.large)"},
        {"name": "vol1_root_size", "prompt": "What is the root volume size (GB)?"},
        {"name": "vol1_volume_type", "prompt": "What is the root volume type (e.g., gp2, gp3)?"},
        {"name": "ec2_ebs2_data_size", "prompt": "What is the data volume size (GB)?"},
    ],
    "s3": [
        {"name": "bucket_name", "prompt": "What would you like to name your S3 bucket?"}
    ],
    "rds": [
        {"name": "db_identifier", "prompt": "What is the DB instance identifier? (e.g., my-rds-instance)"},
        {"name": "db_engine", "prompt": "What database engine would you like? (e.g., mysql, postgres, aurora)"},
        {"name": "db_engine_version", "prompt": "What is the database engine version? (e.g., for postgres: 13.4, 14.5; for mysql: 8.0.28, 5.7.34. Please check AWS RDS documentation for supported versions for your chosen engine and instance class.)"},
        {"name": "db_instance_class", "prompt": "What is the DB instance class? (e.g., db.t3.micro, db.m5.large. Please check AWS RDS documentation for supported instance classes for your chosen engine and version.)"},
        {"name": "allocated_storage", "prompt": "How much allocated storage (GB)? (e.g., 20)"},
        {"name": "db_username", "prompt": "What is the master username?"},
        {"name": "db_password", "prompt": "What is the master password?", "sensitive": True},
        {"name": "db_publicly_accessible", "prompt": "Should the RDS instance be publicly accessible? (yes/no)"},
    ],
    "dynamodb": [
        {"name": "table_name", "prompt": "What is the name of the DynamoDB table?"},
        {"name": "hash_key_name", "prompt": "What is the name of the hash key?"},
        {"name": "hash_key_type", "prompt": "What is the type of the hash key (S, N, or B)?"},
    ],
    "iam_user": [
        {"name": "user_name", "prompt": "What is the name of the IAM user?"}
    ],
    "iam_role": [
        {"name": "role_name", "prompt": "What is the name of the IAM role?"}
    ],
    "iam_policy": [
        {"name": "policy_name", "prompt": "What is the name of the IAM policy?"},
        {"name": "policy_description", "prompt": "What is the description of the IAM policy?"},
        {"name": "policy_document", "prompt": "What is the policy document? (in JSON format)"},
    ],
}

# --- Parameter Definitions for Resource Destruction ---
DESTROY_PARAMS = {
    "ec2": [
        {"name": "instance_id", "prompt": "What is the Instance ID of the EC2 instance to destroy?"}
    ],
    "s3": [
        {"name": "bucket_name", "prompt": "What is the name of the S3 bucket to destroy?"}
    ],
    "rds": [
        {"name": "db_identifier", "prompt": "What is the DB instance identifier to destroy?"}
    ],
    "dynamodb": [
        {"name": "table_name", "prompt": "What is the name of the DynamoDB table to destroy?"}
    ],
    "iam_user": [
        {"name": "user_name", "prompt": "What is the name of the IAM user to destroy?"}
    ],
    "iam_role": [
        {"name": "role_name", "prompt": "What is the name of the IAM role to destroy?"}
    ],
    "iam_policy": [
        {"name": "policy_name", "prompt": "What is the name of the IAM policy to destroy?"}
    ],
}

# --- Resource Identifiers for Display ---
RESOURCE_IDENTIFIERS = {
    "ec2": "Name",
    "s3": "Name",
    "rds": "DBInstanceIdentifier",
    "dynamodb": "TableName",
    "iam_user": "UserName",
    "iam_role": "RoleName",
    "iam_policy": "PolicyName",
}

# --- Resource Identifiers for Destruction ---
RESOURCE_DESTROY_IDS = {
    "ec2": "InstanceId",
    "s3": "Name",
    "rds": "DBInstanceIdentifier",
    "dynamodb": "TableName",
    "iam_user": "UserName",
    "iam_role": "RoleName",
    "iam_policy": "PolicyName",
}

# --- Resource List Functions ---
RESOURCE_LIST_FUNCTIONS = {
    "ec2": "list_ec2",
    "s3": "list_s3_buckets",
    "rds": "list_rds_instances",
    "dynamodb": "list_dynamodb_tables",
    "iam_user": "list_iam_users",
    "iam_role": "list_iam_roles",
    "iam_policy": "list_iam_policies",
}

# --- Parameter Aliases for User Friendliness ---
PARAMETER_ALIASES = {
    "ec2": {
        "name": "ec2_name",
        "instance name": "ec2_name",
        "type": "ec2_type",
        "instance type": "ec2_type",
        "ami": "ec2_ami",
        "ami id": "ec2_ami",
        "root volume size": "vol1_root_size",
        "volume size": "vol1_root_size",
        "root volume type": "vol1_volume_type",
        "volume type": "vol1_volume_type",
        "data volume size": "ec2_ebs2_data_size",
        "availability zone": "ec2_availabilityzone",
        "az": "ec2_availabilityzone",
    },
    "s3": {
        "name": "bucket_name",
        "bucket name": "bucket_name",
    },
    "rds": {
        "username": "db_username",
        "master username": "db_username",
        "password": "db_password",
        "master password": "db_password",
        "engine": "db_engine",
        "engine version": "db_engine_version",
        "instance class": "db_instance_class",
        "allocated storage": "allocated_storage",
        "identifier": "db_identifier",
        "publicly accessible": "db_publicly_accessible",
    },
    "dynamodb": {
        "table name": "table_name",
        "hash key name": "hash_key_name",
        "hash key type": "hash_key_type",
    },
    "iam_user": {
        "user name": "user_name",
    },
    "iam_role": {
        "role name": "role_name",
    },
    "iam_policy": {
        "policy name": "policy_name",
        "policy description": "policy_description",
        "policy document": "policy_document",
    },
}

# --- Helper Functions ---
def get_availability_zones():
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_availability_zones()
        zones = [zone['ZoneName'] for zone in response['AvailabilityZones']]
        return zones
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error fetching availability zones: {e}"})
        return []

def diagnose_error(error_message, traceback_str):
    st.session_state.messages.append({"role": "assistant", "content": "An error occurred. Analyzing the issue..."})

    # Provide specific advice for common errors
    if "InvalidParameterCombination" in error_message:
        user_facing_error_message = "It seems you've provided an unsupported combination of parameters. Please check the AWS documentation for valid combinations (e.g., supported engine versions for your chosen database engine and instance class)."
        if "Cannot find version" in error_message:
            user_facing_error_message += " Specifically, the database engine version you selected might not be available for the chosen engine or region."
    elif "Error: Invalid AWS Access Key ID" in error_message or "Error: InvalidClientTokenId" in error_message:
        user_facing_error_message = "Your AWS credentials seem to be invalid. Please check your AWS Access Key ID and Secret Access Key."
    elif "Error: User has no access to iam:ListAccountAliases" in error_message:
        user_facing_error_message = "Your IAM user does not have the required permissions. Please ensure your user has the `iam:ListAccountAliases` permission."
    else:
        user_facing_error_message = error_message

    st.session_state.messages.append({"role": "assistant", "content": user_facing_error_message})

    # Add a button to show the full traceback
    with st.expander("Show Full Error Log"):
        st.code(traceback_str)

    # Ask the AI for a more focused diagnosis
    diagnosis_prompt = f"""An error occurred during an AWS operation. Please provide a concise diagnosis and a step-by-step solution.
    Error Message: {error_message}
    Traceback: {traceback_str}
    """
    try:
        diagnosis_text, _ = send_to_perplexity(diagnosis_prompt)
        if diagnosis_text:
            st.session_state.messages.append({"role": "assistant", "content": f"**AI Diagnosis:**\n{diagnosis_text}"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Failed to get AI diagnosis."})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Failed to get AI diagnosis: {e}"})


def _validate_db_identifier(identifier: str) -> bool:
    # RDS DB instance identifiers must contain only lowercase letters, numbers, or hyphens.
    # They can't begin or end with a hyphen or contain two consecutive hyphens.
    # The length must be from 1 to 63 characters.
    # For simplicity, we'll enforce lowercase alphanumeric and hyphens, and no consecutive hyphens for now.
    # A more robust regex would be: ^[a-z][a-z0-9-]{0,61}[a-z0-9]$
    # For now, let's use a simpler one that catches the reported error.
    return bool(re.fullmatch(r'^[a-z0-9-]+', identifier)) and '--' not in identifier

def _validate_s3_bucket_name(bucket_name: str) -> bool:
    # S3 bucket naming rules:
    # - Must be unique across all AWS. (Cannot validate here)
    # - Can contain lowercase letters, numbers, and hyphens.
    # - Must begin and end with a lowercase letter or number.
    # - Must be between 3 and 63 characters long.
    # - Cannot contain underscores, periods (.), or be formatted as an IP address.
    # - Cannot begin with xn-- or sth-.
    if not (3 <= len(bucket_name) <= 63):
        return False
    if not re.fullmatch(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', bucket_name):
        return False
    if '..' in bucket_name or '.-' in bucket_name or '-.' in bucket_name:
        return False
    if bucket_name.startswith('xn--') or bucket_name.startswith('sth-'):
        return False
    # Cannot validate uniqueness or IP address format here, as it requires AWS API calls.
    return True

def _find_resource_by_identifier(user_input, resources, resource_type):
    # Try to select by number first
    try:
        selection = int(user_input.strip()) - 1
        if 0 <= selection < len(resources):
            return resources[selection]
    except (ValueError, IndexError):
        pass  # Not a valid number, so we'll try matching by name or ID

    # Try to select by name or ID
    identifier_key = RESOURCE_IDENTIFIERS.get(resource_type)
    destroy_id_key = RESOURCE_DESTROY_IDS.get(resource_type)

    for resource in resources:
        # Check against display name (e.g., EC2 Name tag)
        if identifier_key and resource.get(identifier_key, '').lower() == user_input.lower():
            return resource
        # Check against the actual ID (e.g., InstanceId)
        if destroy_id_key and resource.get(destroy_id_key, '').lower() == user_input.lower():
            return resource
            
    return None

def handle_get_resource_info(attribute):
    if not st.session_state.get('active_context'):
        st.session_state.messages.append({"role": "assistant", "content": "I don't have an active resource in context. Please list or create a resource first."})
        return

    active_context = st.session_state.active_context
    resource_details = active_context.get('details', {})
    
    # Simple mapping from natural language to attribute keys
    attribute_map = {
        "ip address": "instance_ip",
        "ip": "instance_ip",
        "id": "InstanceId",
        "instance id": "InstanceId",
        "name": "Name",
    }

    # Normalize the requested attribute
    normalized_attribute = attribute.lower().replace("_", " ")
    attribute_key = attribute_map.get(normalized_attribute)

    if attribute_key and attribute_key in resource_details:
        value = resource_details[attribute_key]
        st.session_state.messages.append({"role": "assistant", "content": f"The {normalized_attribute} is: {value}"})
    else:
        # If not found in the simple map, try to find it directly in the details
        found = False
        for key, value in resource_details.items():
            if attribute.lower() in key.lower().replace("_", " "):
                st.session_state.messages.append({"role": "assistant", "content": f"The {key.replace('_', ' ')} is: {value}"})
                found = True
                break
        if not found:
            st.session_state.messages.append({"role": "assistant", "content": f"I couldn't find the attribute '{attribute}' for the active resource."})

# --- Main Conversation Handler ---
def execute_user_action(user_message):
    if user_message:
        # Expand alias if it exists
        if user_message in st.session_state.get('aliases', {}):
            user_message = st.session_state.aliases[user_message]
        st.session_state.history.append(user_message)

    if st.session_state.conversation_flow.get("active"):
        handle_active_flow(user_message)
    else:
        handle_intent_recognition(user_message)

def handle_active_flow(user_message):
    flow = st.session_state.conversation_flow
    flow_type = flow.get("type")

    if flow_type == "create_resource":
        handle_create_resource_flow(user_message)
    elif flow_type == "destroy_resource":
        handle_destroy_resource_flow(user_message)
    elif flow_type == "list_resources":
        handle_list_resources(flow["resource_type"])
    elif flow_type == "modify_resource":
        handle_modify_resource_flow(user_message)

def _execute_create_resource(flow):
    resource_type = flow["resource_type"]
    with st.spinner(f"Creating {resource_type.upper()}..."):
        try:
            if resource_type == "s3":
                create_function = getattr(terraform_service, "create_s3_bucket")
            else:
                create_function = getattr(terraform_service, f"create_{resource_type}")
            
            # The create_function now returns a dictionary of the outputs
            outputs = create_function(**flow["params"])
            print(f"DEBUG: Outputs from create_function: {outputs}")

            summary = f"{resource_type.upper()} created successfully!\n"
            for key, val in outputs.items():
                summary += f"- **{key}:** {val}\n"

            st.session_state.messages.append({"role": "assistant", "content": summary})

            # Set the newly created resource as the active context
            st.session_state.active_context = {
                "resource_type": resource_type,
                "details": outputs
            }

            flow["active"] = False
            st.session_state.messages.append({"role": "assistant", "content": "Resource creation process completed."})


        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error creating {resource_type}: {e}"})
            diagnose_error(f"Error creating {resource_type}", traceback.format_exc())
            flow["error_occurred"] = True
            st.session_state.messages.append({"role": "assistant", "content": "Please address the issue. Once you believe it is fixed, type 'retry' to attempt the resource creation again."})

def handle_create_resource_flow(user_message):
    flow = st.session_state.conversation_flow
    resource_type = flow["resource_type"]

    if flow.get("error_occurred"):
        if flow.get("awaiting_param_modification_decision"):
            if "yes" in user_message.lower():
                flow["awaiting_param_modification_decision"] = False
                flow["awaiting_param_to_modify"] = True
                st.session_state.messages.append({"role": "assistant", "content": "Which parameter would you like to change?"})
            elif "no" in user_message.lower():
                flow["awaiting_param_modification_decision"] = False
                flow["error_occurred"] = False
                _execute_create_resource(flow)
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Please answer with 'yes' or 'no'."})
            return

        if flow.get("awaiting_param_to_modify"):
            param_to_modify_input = user_message.strip().lower()
            resource_type = flow["resource_type"]
            aliases = PARAMETER_ALIASES.get(resource_type, {})
            param_to_modify = aliases.get(param_to_modify_input)

            if param_to_modify and param_to_modify in flow["params"]:
                flow["param_to_modify"] = param_to_modify
                flow["awaiting_param_to_modify"] = False
                flow["awaiting_new_param_value"] = True
                st.session_state.messages.append({"role": "assistant", "content": f"What is the new value for {param_to_modify.replace('_', ' ')}?"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Invalid parameter. Please choose one of the parameters you have already provided."})
            return

        if flow.get("awaiting_new_param_value"):
            param_to_modify = flow["param_to_modify"]
            flow["params"][param_to_modify] = user_message.strip()
            flow["awaiting_new_param_value"] = False
            flow["param_to_modify"] = None
            st.session_state.messages.append({"role": "assistant", "content": "Parameter updated. Would you like to modify another parameter? (yes/no)"})
            flow["awaiting_param_modification_decision"] = True # Loop back to see if they want to change more
            return

        if user_message and 'retry' in user_message.lower():
            flow["awaiting_param_modification_decision"] = True
            st.session_state.messages.append({"role": "assistant", "content": "Would you like to modify any parameters before retrying? (yes/no)"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please type 'retry' to continue or 'cancel' to stop."})
        return
        return

    params_for_resource = RESOURCE_PARAMS.get(resource_type, [])
    param_idx = flow.get("current_param_index", 0)

    if user_message:
        prev_param_name = params_for_resource[param_idx - 1]["name"]
        
        # Handle dynamic version selection for RDS
        if resource_type == "rds" and flow.get("awaiting_version_selection"):
            try:
                selection = int(user_message.strip()) - 1
                supported_versions = flow["supported_versions"]
                if 0 <= selection < len(supported_versions):
                    user_message = supported_versions[selection] # Set user_message to the actual version string
                    flow["awaiting_version_selection"] = False
                    del flow["supported_versions"] # Clean up
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "Invalid selection. Please choose a number from the list of available versions."})
                    flow["current_param_index"] = param_idx - 1 
                    return
            except (ValueError, IndexError):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid input. Please enter a number corresponding to the desired version."})
                flow["current_param_index"] = param_idx - 1 
                return
        
        if resource_type == "rds" and prev_param_name == "db_identifier":
            if not _validate_db_identifier(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid DB instance identifier. It must contain only lowercase letters, numbers, or hyphens, and cannot contain two consecutive hyphens. Please try again."})
                flow["current_param_index"] = param_idx - 1 
                return

        if resource_type == "ec2" and prev_param_name == "ec2_ami":
            if not _validate_ami_id(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid AMI ID format. Please provide a valid AMI ID (e.g., ami-0abcdef1234567890)."})
                flow["current_param_index"] = param_idx - 1
                return
        
        if resource_type == "ec2" and prev_param_name == "ec2_type":
            if not _validate_instance_type(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid EC2 Instance Type. Please provide a valid instance type (e.g., t2.micro, m5.large)."})
                flow["current_param_index"] = param_idx - 1
                return

        if resource_type == "ec2" and prev_param_name == "vol1_volume_type":
            if not _validate_volume_type(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid EBS Volume Type. Please provide a valid volume type (e.g., gp2, gp3, io1)."})
                flow["current_param_index"] = param_idx - 1
                return
        
        flow["params"][prev_param_name] = user_message

    if param_idx < len(params_for_resource):
        param_info = params_for_resource[param_idx]

        if resource_type == "rds" and param_info["name"] == "db_engine_version":
            engine = flow["params"].get("db_engine")
            instance_class = flow["params"].get("db_instance_class")

            if engine and instance_class:
                supported_versions = terraform_service.get_supported_rds_engine_versions(engine, instance_class)
                if supported_versions:
                    version_list_str = "Available versions:\n"
                    for i, version in enumerate(supported_versions):
                        version_list_str += f"{i+1}. {version}\n"
                    st.session_state.messages.append({"role": "assistant", "content": f"{param_info['prompt']}\n{version_list_str}"})
                    flow["awaiting_version_selection"] = True
                    flow["supported_versions"] = supported_versions
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"Could not fetch supported versions for {engine} with instance class {instance_class}. Please enter the version manually or check AWS RDS documentation."})
            else:
                st.session_state.messages.append({"role": "assistant", "content": param_info["prompt"]}) # Fallback if engine or instance_class not yet collected
        else:
            st.session_state.messages.append({"role": "assistant", "content": param_info["prompt"]})
        
        flow["current_param_index"] = param_idx + 1
    else:
        _execute_create_resource(flow)

def handle_destroy_resource_flow(user_message):
    flow = st.session_state.conversation_flow
    resource_type = flow["resource_type"]

    # Stage 1: List resources if not already listed
    if "resources" not in flow:
        try:
            list_function = getattr(terraform_service, RESOURCE_LIST_FUNCTIONS[resource_type])
            resources = list_function()
            if not resources:
                st.session_state.messages.append({"role": "assistant", "content": f"No {resource_type.upper()} resources found to destroy."})
                flow["active"] = False
                return
            
            flow["resources"] = resources
            if len(resources) == 1:
                flow["selected_resource"] = resources[0]
                flow["resource_selected"] = True
                st.session_state.messages.append({"role": "assistant", "content": f"You have one {resource_type.upper()}: {resources[0][RESOURCE_IDENTIFIERS[resource_type]]}. Are you sure you want to destroy it? (yes/no)"})
                flow["awaiting_confirmation"] = True
            else:
                resource_list_str = f"Please select a {resource_type.upper()} to destroy by number:\n"
                for i, resource in enumerate(resources):
                    resource_list_str += f"{i+1}. {resource[RESOURCE_IDENTIFIERS[resource_type]]}\n"
                st.session_state.messages.append({"role": "assistant", "content": resource_list_str})
                flow["awaiting_selection"] = True
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error listing {resource_type}s: {e}"})
            diagnose_error(f"Error listing {resource_type}s", traceback.format_exc())
            flow["active"] = False
        return

    # Stage 2: Handle user selection if multiple resources
    if flow.get("awaiting_selection"):
        selected_resource = _find_resource_by_identifier(user_message, flow["resources"], resource_type)
        
        if selected_resource:
            flow["selected_resource"] = selected_resource
            flow["resource_selected"] = True
            flow["awaiting_selection"] = False
            st.session_state.messages.append({"role": "assistant", "content": f"You have selected to destroy: {flow['selected_resource'][RESOURCE_IDENTIFIERS[resource_type]]}. Are you sure? (yes/no)"})
            flow["awaiting_confirmation"] = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Invalid selection. Please choose a number from the list, or provide the resource name or ID."})
        return

    # Stage 3: Handle confirmation and execute destruction
    if flow.get("awaiting_confirmation"):
        if "yes" in user_message.lower():
            resource_id = flow["selected_resource"][RESOURCE_DESTROY_IDS[resource_type]]
            with st.spinner(f"Destroying {resource_type.upper()} {resource_id}..."):
                try:
                    if resource_type == "s3":
                        destroy_function = getattr(terraform_service, "destroy_s3_bucket")
                        response = destroy_function(resource_id) # S3 destroy takes bucket_name, which is resource_id
                    elif resource_type == "sqs":
                        # Extract queue name from QueueUrl
                        queue_name = resource_id.split('/')[-1]
                        destroy_function = getattr(terraform_service, "destroy_sqs")
                        response = destroy_function(queue_name)
                    else:
                        destroy_function = getattr(terraform_service, f"destroy_{resource_type}")
                        response = destroy_function(resource_id)
                    st.session_state.messages.append({"role": "assistant", "content": f"{resource_type.upper()} destroyed successfully!\n{response}"})
                except Exception as e:
                    st.session_state.messages.append({"role": "assistant", "content": f"Error destroying {resource_type.upper()}: {e}"})
                    diagnose_error(f"Error destroying {resource_type.upper()}", traceback.format_exc())
                finally:
                    flow["active"] = False
        elif "no" in user_message.lower():
            st.session_state.messages.append({"role": "assistant", "content": f"Okay, I will not destroy the {resource_type.upper()}."})
            flow["active"] = False
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please reply with 'yes' or 'no'."})

def handle_modify_resource_flow(user_message):
    flow = st.session_state.conversation_flow
    resource_type = flow["resource_type"]

    # Stage 1: List resources if not already listed
    if "resources" not in flow:
        try:
            list_function = getattr(terraform_service, RESOURCE_LIST_FUNCTIONS[resource_type])
            resources = list_function()
            if not resources:
                st.session_state.messages.append({"role": "assistant", "content": f"No {resource_type.upper()} resources found to modify."})
                flow["active"] = False
                return
            
            flow["resources"] = resources
            if len(resources) == 1:
                flow["selected_resource"] = resources[0]
                flow["resource_selected"] = True
                st.session_state.messages.append({"role": "assistant", "content": f"You have one {resource_type.upper()}: {resources[0][RESOURCE_IDENTIFIERS[resource_type]]}. Which parameter would you like to modify? (e.g., vol1_root_size)"})
                flow["awaiting_param_selection"] = True
            else:
                resource_list_str = f"Please select a {resource_type.upper()} to modify by number:\n"
                for i, resource in enumerate(resources):
                    resource_list_str += f"{i+1}. {resource[RESOURCE_IDENTIFIERS[resource_type]]}\n"
                st.session_state.messages.append({"role": "assistant", "content": resource_list_str})
                flow["awaiting_selection"] = True
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error listing {resource_type}s: {e}"})
            diagnose_error(f"Error listing {resource_type}s", traceback.format_exc())
            flow["active"] = False
        return

    # Stage 2: Handle user selection if multiple resources
    if flow.get("awaiting_selection"):
        selected_resource = _find_resource_by_identifier(user_message, flow["resources"], resource_type)
        
        if selected_resource:
            flow["selected_resource"] = selected_resource
            flow["resource_selected"] = True
            flow["awaiting_selection"] = False
            st.session_state.messages.append({"role": "assistant", "content": f"You have selected to modify: {flow['selected_resource'][RESOURCE_IDENTIFIERS[resource_type]]}. Which parameter would you like to modify? (e.g., vol1_root_size)"})
            flow["awaiting_param_selection"] = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Invalid selection. Please choose a number from the list, or provide the resource name or ID."})
        return

    # Stage 3: Handle parameter selection
    if flow.get("awaiting_param_selection"):
        param_name = user_message.strip()
        # Basic validation: check if the parameter is in the EC2 creation params
        valid_params = [p["name"] for p in RESOURCE_PARAMS.get(resource_type, [])]
        if param_name in valid_params:
            flow["param_to_modify"] = param_name
            flow["awaiting_param_selection"] = False
            st.session_state.messages.append({"role": "assistant", "content": f"What is the new value for {param_name}?"})
            flow["awaiting_new_value"] = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": f"Invalid parameter '{param_name}'. Please choose a parameter from the EC2 creation parameters (e.g., vol1_root_size)."})
        return

    # Stage 4: Handle new value input and execute modification
    if flow.get("awaiting_new_value"):
        new_value = user_message.strip()
        instance_id = flow["selected_resource"][RESOURCE_DESTROY_IDS[resource_type]] # InstanceId is used for destroy, but also unique identifier
        param_to_modify = flow["param_to_modify"]

        with st.spinner(f"Modifying {resource_type.upper()} {instance_id}..." ):
            try:
                # Call the new update function in terraform_service
                response = terraform_service.update_ec2_volume_size(instance_id, int(new_value)) # Assuming vol1_root_size is int
                st.session_state.messages.append({"role": "assistant", "content": f"{resource_type.upper()} modified successfully!\n{response}"})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"Error modifying {resource_type.upper()}: {e}"})
                diagnose_error(f"Error modifying {resource_type.upper()}", traceback.format_exc())
            finally:
                flow["active"] = False

def handle_list_all_resources():
    st.session_state.messages.append({"role": "assistant", "content": "Okay, I will list all of your AWS resources."})
    overall_summary = ""
    with st.spinner("Fetching all resource details..."):
        for resource_type, list_func_name in RESOURCE_LIST_FUNCTIONS.items():
            try:
                list_function = getattr(terraform_service, list_func_name)
                resources = list_function()
                if resources:
                    overall_summary += f"\n--- {resource_type.upper()} ---\\n"
                    for i, resource in enumerate(resources):
                        identifier = resource.get(RESOURCE_IDENTIFIERS.get(resource_type, 'Name'), 'N/A')
                        overall_summary += f"{i+1}. {identifier}\\n"
            except Exception as e:
                overall_summary += f"\n--- {resource_type.upper()} ---\\nError: {e}\\n"
    
    if overall_summary:
        st.session_state.messages.append({"role": "assistant", "content": overall_summary})
    else:
        st.session_state.messages.append({"role": "assistant", "content": "No AWS resources found across all categories."})
    
    if "conversation_flow" in st.session_state:
        st.session_state.conversation_flow["active"] = False

def handle_list_resources(resource_type):
    st.session_state.messages.append({"role": "assistant", "content": f"Okay, let me list your {resource_type.upper()} resources."})
    with st.spinner(f"Fetching {resource_type.upper()} resources..."):
        try:
            list_function = getattr(terraform_service, RESOURCE_LIST_FUNCTIONS[resource_type])
            resources = list_function()
            if resources:
                resource_list_str = f"Here are your {resource_type.upper()} resources:\n"
                for i, resource in enumerate(resources):
                    resource_list_str += f"{i+1}. {resource[RESOURCE_IDENTIFIERS[resource_type]]}\n"
                st.session_state.messages.append({"role": "assistant", "content": resource_list_str})

                # If only one resource is listed, set it as the active context
                if len(resources) == 1:
                    st.session_state.active_context = {
                        "resource_type": resource_type,
                        "details": resources[0]
                    }
            else:
                st.session_state.messages.append({"role": "assistant", "content": f"No {resource_type.upper()} resources found."}) 
                st.session_state.active_context = None # Clear active context if no resources are found
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error listing {resource_type.upper()} resources: {e}"})
            diagnose_error(f"Error listing {resource_type.upper()}: {e}", traceback.format_exc())
    if "conversation_flow" in st.session_state:
        st.session_state.conversation_flow["active"] = False



def handle_cost_estimation(user_message):
    st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you estimate the cost of your request."})
    try:
        prompt = f"Please estimate the monthly cost of the following AWS resource request: {user_message}. Provide a breakdown of the costs and any assumptions you made."
        cost_estimation, _ = send_to_perplexity(prompt)
        st.session_state.messages.append({"role": "assistant", "content": cost_estimation})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error estimating cost: {e}"})
        diagnose_error(f"Error estimating cost: {e}", traceback.format_exc())

def handle_list_creatable_resources():
    st.session_state.messages.append({"role": "assistant", "content": "Here are the AWS resources you can create:"})
    resource_list_str = ""
    for resource_type in RESOURCE_PARAMS.keys():
        resource_list_str += f"- {resource_type.replace("_", " ").title()}\n"
    st.session_state.messages.append({"role": "assistant", "content": resource_list_str})
    if "conversation_flow" in st.session_state:
        st.session_state.conversation_flow["active"] = False


def handle_alias(user_message):
    alias_match = re.match(r'alias\s+(.+?)="(.*?)"', user_message)
    if alias_match:
        alias_name = alias_match.group(1).strip()
        command = alias_match.group(2).strip()
        st.session_state.aliases[alias_name] = command
        st.session_state.messages.append({"role": "assistant", "content": f"Alias '{alias_name}' created for command: '{command}'"})
    elif user_message.strip() == 'alias':
        if st.session_state.aliases:
            alias_list_str = "Here are your current aliases:\n"
            for name, command in st.session_state.aliases.items():
                alias_list_str += f"- {name}: \"{command}\"\n"
            st.session_state.messages.append({"role": "assistant", "content": alias_list_str})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "You have no aliases defined."})
    else:
        st.session_state.messages.append({"role": "assistant", "content": "Invalid alias command. Use 'alias <name>=\"<command>\"' to create an alias, or 'alias' to list your aliases."})

def handle_history():

    st.session_state.messages.append({"role": "assistant", "content": "Here is your command history:"})
    history_str = ""
    for i, command in enumerate(st.session_state.history):
        history_str += f"{i+1}. {command}\n"
    st.session_state.messages.append({"role": "assistant", "content": history_str})

def handle_intent_recognition(user_message):

    if not user_message: return
    lower_message = user_message.lower()

    # Check for contextual commands if there is an active context
    if st.session_state.get('active_context'):
        if re.search(r'\b(destroy|delete|terminate)( it)?\b', lower_message):
            st.session_state.messages.append({"role": "assistant", "content": f"Okay, I will destroy the active resource."})
            st.session_state.conversation_flow = {
                "active": True,
                "type": "destroy_resource",
                "resource_type": st.session_state.active_context['resource_type'],
                "resources": [st.session_state.active_context['details']],
                "selected_resource": st.session_state.active_context['details'],
                "resource_selected": True,
                "awaiting_confirmation": True
            }
            st.session_state.messages.append({"role": "assistant", "content": f"You have selected to destroy: {st.session_state.active_context['details'][RESOURCE_IDENTIFIERS[st.session_state.active_context['resource_type']]]}. Are you sure? (yes/no)"})
            return False
        elif re.search(r'\b(modify|change|update)( it)?\b', lower_message):
            st.session_state.messages.append({"role": "assistant", "content": f"Okay, I will modify the active resource."})
            st.session_state.conversation_flow = {
                "active": True,
                "type": "modify_resource",
                "resource_type": st.session_state.active_context['resource_type'],
                "resources": [st.session_state.active_context['details']],
                "selected_resource": st.session_state.active_context['details'],
                "resource_selected": True,
                "awaiting_param_selection": True
            }
            st.session_state.messages.append({"role": "assistant", "content": f"You have selected to modify: {st.session_state.active_context['details'][RESOURCE_IDENTIFIERS[st.session_state.active_context['resource_type']]]}. Which parameter would you like to modify? (e.g., vol1_root_size)"})
            return False
        elif re.search(r'what is its (.*)\b', lower_message):
            match = re.search(r'what is its (.*)\b', lower_message)
            attribute = match.group(1).strip()
            handle_get_resource_info(attribute)
            return False

    # --- Create Resource Intents ---
    if re.search(r'\b(create|build|launch)\s+(an\s+)?ec2(\s+instance)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an EC2 instance."})
        zones = get_availability_zones()
        if not zones:
            st.session_state.messages.append({"role": "assistant", "content": "Could not fetch availability zones. Please specify one manually."})
        
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "ec2",
            "params": {},
            "current_param_index": 0,
            "availability_zones": zones # Store zones for validation
        }
        handle_create_resource_flow(None) # Start the flow
        return False
    elif re.search(r'\b(create|make)\s+(an\s+)?s3(\s+bucket)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an S3 bucket."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "s3",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+(an\s+)?rds(\s+instance)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an RDS instance."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "rds",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+(a\s+)?dynamodb(\s+table)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create a DynamoDB table."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "dynamodb",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+sns\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an SNS topic."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+(an\s+)?iam\s+user\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an IAM user."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "iam_user",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+(an\s+)?iam\s+role\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an IAM role."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "iam_role",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False
    elif re.search(r'\b(create|make)\s+(an\s+)?iam\s+policy\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you create an IAM policy."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": "iam_policy",
            "params": {},
            "current_param_index": 0,
        }
        handle_create_resource_flow(None)
        return False

    # --- Destroy Resource Intents ---
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?(ec2|instance)\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an EC2 instance."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "ec2",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?s3(\s+bucket)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an S3 bucket."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "s3",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?rds(\s+instance)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an RDS instance."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "rds",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(a\s+)?dynamodb(\s+table)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy a DynamoDB table."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "dynamodb",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?iam\s+user\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an IAM user."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "iam_user",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?iam\s+role\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an IAM role."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "iam_role",
        }
        handle_destroy_resource_flow(None)
        return False
    elif re.search(r'\b(destroy|delete|terminate)\s+(an\s+)?iam\s+policy\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you destroy an IAM policy."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "destroy_resource",
            "resource_type": "iam_policy",
        }
        handle_destroy_resource_flow(None)
        return False

    # --- List Resources Intent ---
    elif re.search(r'\b(list|show)\s+(all\s+)?(ec2|instance)s?\b', lower_message):
        handle_list_resources("ec2")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?s3(\s+buckets?)?\b', lower_message):
        handle_list_resources("s3")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?rds(\s+instances?)?\b', lower_message):
        handle_list_resources("rds")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?dynamodb(\s+tables?)?\b', lower_message):
        handle_list_resources("dynamodb")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?iam\s+users?\b', lower_message):
        handle_list_resources("iam_user")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?iam\s+roles?\b', lower_message):
        handle_list_resources("iam_role")
        return False
    elif re.search(r'\b(list|show)\s+(all\s+)?iam\s+policies?\b', lower_message):
        handle_list_resources("iam_policy")
        return False

    # --- Cost Estimation Intent ---
    elif re.search(r'\b(cost of|estimate cost)\b', lower_message):
        handle_cost_estimation(user_message)
        return False

    # --- List Creatable Resources Intent ---
    elif re.search(r'\b(what aws resources can be created|list creatable resources|what resources can i create)\b', lower_message):
        handle_list_creatable_resources()
        return False

    # --- History Intent ---
    elif lower_message == 'history':
        handle_history()
        return False

    # --- Alias Intent ---
    elif lower_message.startswith('alias'):
        handle_alias(user_message)
        return False

    # --- Modify Resource Intents ---
    elif re.search(r'\b(modify|change|update)\s+(an\s+)?(ec2|instance)(\s+instance)?\b', lower_message):
        st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you modify an EC2 instance."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "modify_resource",
            "resource_type": "ec2",
        }
        handle_modify_resource_flow(None) # Start the flow
        return False

    else:
        ai_response, err = send_to_perplexity(user_message)
        if err:
            st.session_state.messages.append({"role": "assistant", "content": f"AI communication failed: {err}"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
