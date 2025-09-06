import streamlit as st
import re
import traceback
import boto3
import json
from services import terraform_service
from services.terraform_service import _validate_ami_id, _validate_instance_type, _validate_volume_type
from utils.ai_client import send_to_perplexity

# Import enhanced AI conversation modules
from utils.intent_classifier import classify_intent, get_intent_suggestions
from utils.context_manager import get_context, update_context, add_message_to_history, get_recent_history, learn_from_interaction, get_smart_defaults
from utils.parameter_extractor import extract_parameters, get_missing_parameters, suggest_parameter_values
from utils.suggestion_engine import get_proactive_suggestions, get_contextual_help, get_ai_powered_suggestions
from utils.error_recovery import analyze_error, get_error_context_help, generate_error_report

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

def diagnose_error(error_message, traceback_str, intent="", parameters=None, session_id="default_session"):
    """
    Enhanced error diagnosis using AI-powered analysis and recovery suggestions.
    """
    st.session_state.messages.append({"role": "assistant", "content": "🔍 An error occurred. Analyzing the issue..."})

    # Use enhanced error analysis
    error_analysis = analyze_error(error_message, traceback_str, intent, parameters or {})

    # Display error severity and type
    severity_emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}.get(error_analysis['severity'], "⚠️")
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"{severity_emoji} **{error_analysis['error_type'].title()} Error** (Severity: {error_analysis['severity'].title()})"
    })

    # Display root cause if available
    if error_analysis.get('root_cause'):
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**Root Cause:** {error_analysis['root_cause']}"
        })

    # Display recovery steps
    if error_analysis.get('recovery_steps'):
        recovery_text = "**Recovery Steps:**\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(error_analysis['recovery_steps'])])
        st.session_state.messages.append({"role": "assistant", "content": recovery_text})

    # Display preventive measures
    if error_analysis.get('preventive_measures'):
        preventive_text = "**Preventive Measures:**\n" + "\n".join([f"• {measure}" for measure in error_analysis['preventive_measures']])
        st.session_state.messages.append({"role": "assistant", "content": preventive_text})

    # Get contextual help
    help_messages = get_error_context_help(error_analysis)
    if help_messages:
        help_text = "**Additional Help:**\n" + "\n".join([f"• {msg}" for msg in help_messages])
        st.session_state.messages.append({"role": "assistant", "content": help_text})

    # Add detailed error log in expander
    with st.expander("🔧 Show Full Error Details"):
        st.code(traceback_str)

        # Show comprehensive error report
        if intent and parameters:
            error_report = generate_error_report(error_message, traceback_str, intent, parameters)
            st.markdown("### 📋 Complete Error Report")
            st.markdown(error_report)

    # Update conversation context with error information
    update_context(session_id, error_context=error_analysis, conversation_state="error")

    # Provide retry option for recoverable errors
    if error_analysis['severity'] in ['low', 'medium']:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "💡 This error appears recoverable. You can try 'retry' to attempt the operation again, or 'modify' to change parameters."
        })


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

def _find_parameter_by_input(user_input, resource_type, current_params):
    """Find parameter name by user input (supports aliases and fuzzy matching)"""
    user_input_lower = user_input.lower().strip()

    # Get aliases for this resource type
    aliases = PARAMETER_ALIASES.get(resource_type, {})

    # First, check exact aliases
    for alias, param_name in aliases.items():
        if alias == user_input_lower:
            return param_name

    # Check if user input matches parameter name directly
    for param_name in current_params.keys():
        if param_name.lower() == user_input_lower:
            return param_name

    # Fuzzy matching - check if user input contains key parts of parameter names
    param_keywords = {
        # EC2 parameters
        'ec2_name': ['name', 'instance name', 'server name', 'ec2 name'],
        'ec2_ami': ['ami', 'ami id', 'image', 'image id', 'amazon machine image'],
        'ec2_type': ['type', 'instance type', 'size', 'instance size', 'machine type'],
        'ec2_availabilityzone': ['zone', 'availability zone', 'az', 'region zone'],
        'vol1_root_size': ['root', 'root size', 'volume size', 'disk size', 'root disk', 'boot volume'],
        'vol1_volume_type': ['volume type', 'disk type', 'storage type', 'root volume type'],
        'ec2_ebs2_data_size': ['data', 'data size', 'data volume', 'additional storage', 'ebs size'],

        # S3 parameters
        'bucket_name': ['bucket', 'bucket name', 's3 bucket', 'storage bucket'],

        # RDS parameters
        'db_identifier': ['identifier', 'db name', 'database name', 'db identifier', 'rds name'],
        'db_engine': ['engine', 'database engine', 'db engine', 'rds engine'],
        'db_engine_version': ['version', 'engine version', 'db version', 'rds version'],
        'db_instance_class': ['class', 'instance class', 'db class', 'rds class', 'size'],
        'allocated_storage': ['storage', 'allocated storage', 'db storage', 'disk size'],
        'db_username': ['username', 'user', 'db user', 'database user', 'admin user'],
        'db_password': ['password', 'db password', 'database password', 'admin password'],
        'db_publicly_accessible': ['public', 'publicly accessible', 'public access', 'internet access'],

        # DynamoDB parameters
        'table_name': ['table', 'table name', 'dynamodb table'],
        'hash_key_name': ['hash key', 'key name', 'primary key', 'partition key'],
        'hash_key_type': ['key type', 'hash key type', 'attribute type', 'data type']
    }

    for param_name, keywords in param_keywords.items():
        if param_name in current_params:  # Only suggest parameters that are actually in use
            for keyword in keywords:
                if keyword in user_input_lower:
                    return param_name

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

        # Add message to context history for enhanced AI processing
        session_id = st.session_state.get('session_id', 'default_session')
        user_msg = {"role": "user", "content": user_message}
        add_message_to_history(session_id, user_msg)

    if st.session_state.conversation_flow.get("active"):
        handle_active_flow(user_message)
    else:
        handle_enhanced_intent_recognition(user_message)

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

def _show_resource_preview(flow):
    """Show a preview of the resource configuration before creation"""
    resource_type = flow["resource_type"]
    params = flow["params"]

    # Create a human-readable preview
    preview_text = f"## 📋 **{resource_type.upper()} Resource Preview**\n\n"

    # Map parameter names to human-readable labels for all resource types
    param_labels = {
        # EC2 parameters
        'ec2_name': 'Instance Name',
        'ec2_ami': 'AMI ID',
        'ec2_type': 'Instance Type',
        'ec2_availabilityzone': 'Availability Zone',
        'vol1_root_size': 'Root Volume Size (GB)',
        'vol1_volume_type': 'Root Volume Type',
        'ec2_ebs2_data_size': 'Data Volume Size (GB)',

        # S3 parameters
        'bucket_name': 'Bucket Name',

        # RDS parameters
        'db_identifier': 'Database Identifier',
        'db_engine': 'Database Engine',
        'db_engine_version': 'Engine Version',
        'db_instance_class': 'Instance Class',
        'allocated_storage': 'Storage (GB)',
        'db_username': 'Username',
        'db_password': 'Password',
        'db_publicly_accessible': 'Publicly Accessible',

        # DynamoDB parameters
        'table_name': 'Table Name',
        'hash_key_name': 'Hash Key Name',
        'hash_key_type': 'Hash Key Type'
    }

    preview_text += "**Configuration:**\n"
    for param_key, param_value in params.items():
        label = param_labels.get(param_key, param_key.replace('_', ' ').title())

        # Mask sensitive information
        if 'password' in param_key.lower():
            display_value = "••••••••"
        else:
            display_value = param_value

        preview_text += f"- **{label}:** {display_value}\n"

    # Resource-specific warnings and notes
    preview_text += "\n**⚠️ Important Notes:**\n"

    if resource_type == 'ec2':
        preview_text += "- 💰 **EC2 instances will incur charges while running**\n"
        preview_text += "- 🔍 Make sure the AMI ID is valid for your region\n"
        preview_text += "- 💾 Root volume will be created with the specified type and size\n"

    elif resource_type == 'rds':
        preview_text += "- 💰 **RDS instances will incur charges while running**\n"
        preview_text += "- 🔐 Database credentials will be stored securely\n"
        preview_text += "- 📊 Storage costs apply based on allocated size\n"
        preview_text += "- 🌐 Consider security group and subnet settings\n"

    elif resource_type == 's3':
        preview_text += "- 🌍 **S3 bucket names are globally unique**\n"
        preview_text += "- 💰 Standard S3 charges apply for storage, requests, and data transfer\n"
        preview_text += "- 🔒 Consider enabling versioning and encryption for production use\n"
        preview_text += "- 📍 Bucket will be created in your default region\n"

    elif resource_type == 'dynamodb':
        preview_text += "- 💰 **DynamoDB charges based on throughput and storage**\n"
        preview_text += "- 🔑 Primary key configuration affects performance\n"
        preview_text += "- 📈 Consider read/write capacity settings for cost optimization\n"

    # Cost estimation if possible
    if resource_type == 'ec2' and 'ec2_type' in params:
        instance_type = params.get('ec2_type', '').lower()
        if 't3.micro' in instance_type:
            preview_text += "- 💵 **Estimated cost:** ~$8-10/month (t3.micro, minimal usage)\n"
        elif 't3.small' in instance_type:
            preview_text += "- 💵 **Estimated cost:** ~$15-20/month (t3.small, minimal usage)\n"

    elif resource_type == 'rds' and 'db_instance_class' in params:
        db_class = params.get('db_instance_class', '').lower()
        if 'db.t3.micro' in db_class:
            preview_text += "- 💵 **Estimated cost:** ~$15-25/month (db.t3.micro, minimal usage)\n"

    preview_text += "\n**🚀 Ready to create this resource?**\n"
    preview_text += "**Type 'yes' to create, 'modify' to change parameters, or 'cancel' to abort.**"

    st.session_state.messages.append({"role": "assistant", "content": preview_text})
    flow["awaiting_confirmation"] = True

def _show_modify_preview(flow):
    """Show a preview of the resource modification before execution"""
    resource_type = flow["resource_type"]
    params = flow.get("params", {})
    selected_resource = flow["selected_resource"]

    # Create a human-readable preview
    resource_name = selected_resource.get(RESOURCE_IDENTIFIERS[resource_type], 'Unknown')
    preview_text = f"## 🔧 **Modify {resource_type.upper()} Resource: {resource_name}**\n\n"

    # Map parameter names to human-readable labels for all resource types
    param_labels = {
        # EC2 parameters
        'ec2_name': 'Instance Name',
        'ec2_ami': 'AMI ID',
        'ec2_type': 'Instance Type',
        'ec2_availabilityzone': 'Availability Zone',
        'vol1_root_size': 'Root Volume Size (GB)',
        'vol1_volume_type': 'Root Volume Type',
        'ec2_ebs2_data_size': 'Data Volume Size (GB)',

        # S3 parameters
        'bucket_name': 'Bucket Name',

        # RDS parameters
        'db_identifier': 'Database Identifier',
        'db_engine': 'Database Engine',
        'db_engine_version': 'Engine Version',
        'db_instance_class': 'Instance Class',
        'allocated_storage': 'Storage (GB)',
        'db_username': 'Username',
        'db_password': 'Password',
        'db_publicly_accessible': 'Publicly Accessible',

        # DynamoDB parameters
        'table_name': 'Table Name',
        'hash_key_name': 'Hash Key Name',
        'hash_key_type': 'Hash Key Type'
    }

    preview_text += "**Proposed Changes:**\n"
    for param_key, param_value in params.items():
        label = param_labels.get(param_key, param_key.replace('_', ' ').title())

        # Mask sensitive information
        if 'password' in param_key.lower():
            display_value = "••••••••"
        else:
            display_value = param_value

        preview_text += f"- **{label}:** {display_value}\n"

    # Resource-specific warnings and notes
    preview_text += "\n**⚠️ Important Notes:**\n"

    if resource_type == 'ec2':
        preview_text += "- 🔄 **EC2 modifications may require instance restart**\n"
        preview_text += "- 💰 **Additional charges may apply for larger volumes**\n"
        preview_text += "- ⏱️ **Volume modifications may take time to complete**\n"

    elif resource_type == 'rds':
        preview_text += "- 🔄 **RDS modifications may cause downtime**\n"
        preview_text += "- 💰 **Storage increases will incur additional charges**\n"
        preview_text += "- ⏱️ **Some changes require instance restart**\n"

    elif resource_type == 's3':
        preview_text += "- ⚠️ **Bucket name changes are not supported**\n"
        preview_text += "- 🔒 **Ensure proper permissions for modifications**\n"

    elif resource_type == 'dynamodb':
        preview_text += "- 🔄 **Table modifications may affect performance**\n"
        preview_text += "- 💰 **Throughput changes will affect billing**\n"

    preview_text += "\n**🚀 Ready to apply these modifications?**\n"
    preview_text += "**Type 'yes' to proceed, 'modify' to change parameters, or 'cancel' to abort.**"

    st.session_state.messages.append({"role": "assistant", "content": preview_text})
    flow["awaiting_confirmation"] = True

def _extract_current_resource_params(resource, resource_type):
    """Extract current parameter values from a resource for modification preview"""
    params = {}

    # Map resource attributes to parameter names based on resource type
    if resource_type == 'ec2':
        # Extract EC2-specific parameters
        if 'InstanceId' in resource:
            params['instance_id'] = resource['InstanceId']
        if 'InstanceType' in resource:
            params['ec2_type'] = resource['InstanceType']
        if 'ImageId' in resource:
            params['ec2_ami'] = resource['ImageId']
        if 'Placement' in resource and 'AvailabilityZone' in resource['Placement']:
            params['ec2_availabilityzone'] = resource['Placement']['AvailabilityZone']

        # Extract volume information
        if 'BlockDeviceMappings' in resource:
            for mapping in resource['BlockDeviceMappings']:
                if mapping.get('DeviceName') == '/dev/sda1' or mapping.get('DeviceName') == '/dev/xvda':
                    if 'Ebs' in mapping:
                        ebs = mapping['Ebs']
                        if 'Size' in ebs:
                            params['vol1_root_size'] = str(ebs['Size'])
                        if 'VolumeType' in ebs:
                            params['vol1_volume_type'] = ebs['VolumeType']

    elif resource_type == 'rds':
        # Extract RDS-specific parameters
        if 'DBInstanceIdentifier' in resource:
            params['db_identifier'] = resource['DBInstanceIdentifier']
        if 'Engine' in resource:
            params['db_engine'] = resource['Engine']
        if 'EngineVersion' in resource:
            params['db_engine_version'] = resource['EngineVersion']
        if 'DBInstanceClass' in resource:
            params['db_instance_class'] = resource['DBInstanceClass']
        if 'AllocatedStorage' in resource:
            params['allocated_storage'] = str(resource['AllocatedStorage'])
        if 'MasterUsername' in resource:
            params['db_username'] = resource['MasterUsername']
        if 'PubliclyAccessible' in resource:
            params['db_publicly_accessible'] = 'yes' if resource['PubliclyAccessible'] else 'no'

    elif resource_type == 's3':
        # Extract S3-specific parameters
        if 'Name' in resource:
            params['bucket_name'] = resource['Name']

    elif resource_type == 'dynamodb':
        # Extract DynamoDB-specific parameters
        if 'TableName' in resource:
            params['table_name'] = resource['TableName']
        if 'KeySchema' in resource:
            for key in resource['KeySchema']:
                if key.get('KeyType') == 'HASH':
                    if 'AttributeName' in key:
                        params['hash_key_name'] = key['AttributeName']
                    # Find the attribute type
                    if 'AttributeDefinitions' in resource:
                        for attr in resource['AttributeDefinitions']:
                            if attr.get('AttributeName') == key.get('AttributeName'):
                                params['hash_key_type'] = attr.get('AttributeType', 'S')
                                break

    elif resource_type == 'iam_user':
        # Extract IAM User-specific parameters
        if 'UserName' in resource:
            params['user_name'] = resource['UserName']
        if 'UserId' in resource:
            params['user_id'] = resource['UserId']
        if 'CreateDate' in resource:
            params['create_date'] = str(resource['CreateDate'])

    elif resource_type == 'iam_role':
        # Extract IAM Role-specific parameters
        if 'RoleName' in resource:
            params['role_name'] = resource['RoleName']
        if 'RoleId' in resource:
            params['role_id'] = resource['RoleId']
        if 'CreateDate' in resource:
            params['create_date'] = str(resource['CreateDate'])

    elif resource_type == 'iam_policy':
        # Extract IAM Policy-specific parameters
        if 'PolicyName' in resource:
            params['policy_name'] = resource['PolicyName']
        if 'PolicyId' in resource:
            params['policy_id'] = resource['PolicyId']
        if 'Description' in resource:
            params['policy_description'] = resource['Description']
        if 'CreateDate' in resource:
            params['create_date'] = str(resource['CreateDate'])

    return params

def _execute_modify_resource(flow):
    """Execute the resource modification"""
    resource_type = flow["resource_type"]
    selected_resource = flow["selected_resource"]
    params = flow.get("params", {})

    # Get the resource identifier for modification
    resource_id = selected_resource[RESOURCE_DESTROY_IDS[resource_type]]

    with st.spinner(f"Modifying {resource_type.upper()} {resource_id}..."):
        try:
            # Call the appropriate modification function based on resource type and parameters
            if resource_type == "ec2":
                # Handle EC2 modifications
                if 'vol1_root_size' in params:
                    response = terraform_service.update_ec2_volume_size(resource_id, int(params['vol1_root_size']))
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **EC2 instance modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Root Volume Size\n**New Value:** {params['vol1_root_size']} GB\n\n{response}"})
                elif 'ec2_type' in params:
                    response = terraform_service.update_ec2_instance_type(resource_id, params['ec2_type'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **EC2 instance modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Instance Type\n**New Value:** {params['ec2_type']}\n\n{response}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification of the specified parameter is not yet supported for EC2 instances."})

            elif resource_type == "rds":
                # Handle RDS modifications
                if 'allocated_storage' in params:
                    response = terraform_service.update_rds_storage(resource_id, int(params['allocated_storage']))
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **RDS instance modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Allocated Storage\n**New Value:** {params['allocated_storage']} GB\n\n{response}"})
                elif 'db_instance_class' in params:
                    response = terraform_service.update_rds_instance_class(resource_id, params['db_instance_class'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **RDS instance modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Instance Class\n**New Value:** {params['db_instance_class']}\n\n{response}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification of the specified parameter is not yet supported for RDS instances."})

            elif resource_type == "iam_user":
                # Handle IAM User modifications
                if 'user_name' in params:
                    response = terraform_service.update_iam_user_name(resource_id, params['user_name'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **IAM User modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** User Name\n**New Value:** {params['user_name']}\n\n{response}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification of the specified parameter is not yet supported for IAM Users."})

            elif resource_type == "iam_role":
                # Handle IAM Role modifications
                if 'role_name' in params:
                    response = terraform_service.update_iam_role_name(resource_id, params['role_name'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **IAM Role modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Role Name\n**New Value:** {params['role_name']}\n\n{response}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification of the specified parameter is not yet supported for IAM Roles."})

            elif resource_type == "iam_policy":
                # Handle IAM Policy modifications
                if 'policy_name' in params:
                    response = terraform_service.update_iam_policy_name(resource_id, params['policy_name'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **IAM Policy modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Policy Name\n**New Value:** {params['policy_name']}\n\n{response}"})
                elif 'policy_description' in params:
                    response = terraform_service.update_iam_policy_description(resource_id, params['policy_description'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **IAM Policy modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Policy Description\n**New Value:** {params['policy_description']}\n\n{response}"})
                elif 'policy_document' in params:
                    response = terraform_service.update_iam_policy_document(resource_id, params['policy_document'])
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ **IAM Policy modified successfully!**\n\n**Resource:** {resource_id}\n**Parameter Updated:** Policy Document\n**New Value:** [JSON Document]\n\n{response}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification of the specified parameter is not yet supported for IAM Policies."})

            else:
                # For other resource types, show a generic message
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Modification is not yet supported for {resource_type.upper()} resources."})

            # Update context with modification information
            session_id = st.session_state.get('session_id', 'default_session')
            update_context(session_id, last_action=f"modified_{resource_type}", modified_resource_id=resource_id)

        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Error modifying {resource_type.upper()}: {e}"})
            session_id = st.session_state.get('session_id', 'default_session')
            diagnose_error(
                f"Error modifying {resource_type.upper()}",
                traceback.format_exc(),
                f"modify_{resource_type}",
                params,
                session_id
            )
        finally:
            flow["active"] = False

def _execute_create_resource(flow):
    resource_type = flow["resource_type"]

    # First, show preview if not already shown
    if not flow.get("preview_shown"):
        _show_resource_preview(flow)
        flow["preview_shown"] = True
        return

    # If we get here, user has confirmed, so proceed with creation
    with st.spinner(f"Creating {resource_type.upper()}..."):
        try:
            if resource_type == "s3":
                create_function = getattr(terraform_service, "create_s3_bucket")
            else:
                create_function = getattr(terraform_service, f"create_{resource_type}")

            # The create_function now returns a dictionary of the outputs
            outputs = create_function(**flow["params"])
            print(f"DEBUG: Outputs from create_function: {outputs}")

            summary = f"✅ **{resource_type.upper()} created successfully!**\n\n"
            summary += "**Resource Details:**\n"
            for key, val in outputs.items():
                summary += f"- **{key}:** {val}\n"

            st.session_state.messages.append({"role": "assistant", "content": summary})

            # Set the newly created resource as the active context
            st.session_state.active_context = {
                "resource_type": resource_type,
                "details": outputs
            }

            flow["active"] = False
            st.session_state.messages.append({"role": "assistant", "content": "🎉 Resource creation process completed successfully!"})


        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Error creating {resource_type}: {e}"})
            session_id = st.session_state.get('session_id', 'default_session')
            diagnose_error(
                f"Error creating {resource_type}",
                traceback.format_exc(),
                f"create_{resource_type}",
                flow.get("params", {}),
                session_id
            )
            flow["error_occurred"] = True
            st.session_state.messages.append({"role": "assistant", "content": "💡 **Recovery Options:**\n- Type 'retry' to attempt again\n- Type 'modify' to change parameters\n- Type 'cancel' to abort"})

def handle_create_resource_flow(user_message):
    flow = st.session_state.conversation_flow
    resource_type = flow["resource_type"]

    # Fix: Skip parameters that are already provided in the params dictionary
    # This prevents asking for parameters that were already extracted from the initial message
    if flow.get("current_param_index") is not None:
        params = flow.get("params", {})
        params_for_resource = RESOURCE_PARAMS.get(resource_type, [])

        # Skip any parameters that are already provided
        while (flow["current_param_index"] < len(params_for_resource) and
               params_for_resource[flow["current_param_index"]]["name"] in params):
            flow["current_param_index"] += 1

    # Handle confirmation step
    if flow.get("awaiting_confirmation"):
        if user_message.lower() in ['yes', 'y', 'confirm', 'proceed']:
            flow["awaiting_confirmation"] = False
            flow["confirmed"] = True
            _execute_create_resource(flow)
        elif user_message.lower() in ['modify', 'change', 'edit']:
            flow["awaiting_confirmation"] = False
            flow["awaiting_param_modification_decision"] = True
            st.session_state.messages.append({"role": "assistant", "content": "🔧 **Parameter Modification**\n\nWhich parameter would you like to change? You can specify:\n- Parameter name (e.g., 'instance type', 'volume size')\n- Or type 'list' to see all current parameters"})
        elif user_message.lower() in ['cancel', 'abort', 'no', 'n']:
            flow["active"] = False
            st.session_state.messages.append({"role": "assistant", "content": "❌ Resource creation cancelled."})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please respond with:\n- **'yes'** to create the resource\n- **'modify'** to change parameters\n- **'cancel'** to abort"})
        return

    # Handle parameter modification
    if flow.get("awaiting_param_modification_decision"):
        if user_message.lower() in ['list', 'show', 'current']:
            # Show current parameters
            current_params = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in flow["params"].items()])
            st.session_state.messages.append({"role": "assistant", "content": f"📋 **Current Parameters:**\n{current_params}\n\nWhich parameter would you like to change?"})
            return
        elif user_message.lower() in ['done', 'finished', 'proceed']:
            flow["awaiting_param_modification_decision"] = False
            _show_resource_preview(flow)  # Show preview again
            return
        else:
            # Try to match parameter
            param_to_modify = _find_parameter_by_input(user_message, resource_type, flow["params"])
            if param_to_modify:
                flow["param_to_modify"] = param_to_modify
                flow["awaiting_param_modification_decision"] = False
                flow["awaiting_new_param_value"] = True
                current_value = flow["params"].get(param_to_modify, "Not set")
                st.session_state.messages.append({"role": "assistant", "content": f"Current value for **{param_to_modify.replace('_', ' ').title()}**: {current_value}\n\nWhat is the new value?"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "❌ Parameter not found. Please specify a valid parameter name or type 'list' to see all parameters."})
            return

    if flow.get("awaiting_new_param_value"):
        param_to_modify = flow["param_to_modify"]
        flow["params"][param_to_modify] = user_message.strip()
        flow["awaiting_new_param_value"] = False
        flow["param_to_modify"] = None
        st.session_state.messages.append({"role": "assistant", "content": f"✅ Parameter updated! **{param_to_modify.replace('_', ' ').title()}** is now: {user_message.strip()}\n\nWould you like to modify another parameter? (yes/no)"})
        flow["awaiting_param_modification_decision"] = True
        return

    # Handle error recovery
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
            flow["awaiting_param_modification_decision"] = True
            return

        if user_message and 'retry' in user_message.lower():
            flow["awaiting_param_modification_decision"] = True
            st.session_state.messages.append({"role": "assistant", "content": "Would you like to modify any parameters before retrying? (yes/no)"})
        elif user_message and 'cancel' in user_message.lower():
            flow["active"] = False
            flow["error_occurred"] = False
            st.session_state.messages.append({"role": "assistant", "content": "❌ Resource creation cancelled."})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please type 'retry' to continue or 'cancel' to stop."})
        return

    params_for_resource = RESOURCE_PARAMS.get(resource_type, [])
    param_idx = flow.get("current_param_index", 0)

    if user_message:
        # Get the parameter that was actually asked for, not just the previous index
        current_param_name = flow.get("current_param_name")
        if not current_param_name and param_idx > 0:
            current_param_name = params_for_resource[param_idx - 1]["name"]
        elif not current_param_name:
            # Fallback if no current_param_name is set
            current_param_name = params_for_resource[param_idx]["name"] if param_idx < len(params_for_resource) else None

        if not current_param_name:
            st.session_state.messages.append({"role": "assistant", "content": "❌ Error: Could not determine which parameter to update. Please try again."})
            return

        prev_param_name = current_param_name

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

        # Validate parameters before storing them
        validation_passed = True

        if resource_type == "rds" and prev_param_name == "db_identifier":
            if not _validate_db_identifier(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid DB instance identifier. It must contain only lowercase letters, numbers, or hyphens, and cannot contain two consecutive hyphens. Please try again."})
                validation_passed = False

        if resource_type == "ec2" and prev_param_name == "ec2_ami":
            if not _validate_ami_id(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid AMI ID format. Please provide a valid AMI ID (e.g., ami-0abcdef1234567890)."})
                validation_passed = False

        if resource_type == "ec2" and prev_param_name == "ec2_type":
            if not _validate_instance_type(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid EC2 Instance Type. Please provide a valid instance type (e.g., t2.micro, m5.large)."})
                validation_passed = False

        if resource_type == "ec2" and prev_param_name == "vol1_volume_type":
            if not _validate_volume_type(user_message):
                st.session_state.messages.append({"role": "assistant", "content": "Invalid EBS Volume Type. Please provide a valid volume type (e.g., gp2, gp3, io1)."})
                validation_passed = False

        # Only store the parameter if validation passed
        if validation_passed:
            flow["params"][prev_param_name] = user_message
            # Clear the current_param_name since we've successfully processed this parameter
            flow["current_param_name"] = None
        else:
            # Validation failed, don't increment index and keep current_param_name for re-asking
            return  # Don't continue if validation failed

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
            # Store the current parameter name for later use when processing response
            flow["current_param_name"] = param_info["name"]

            # Check if this is an enhanced flow and provide suggestions
            if flow.get("enhanced_flow") and flow.get("missing_params"):
                param_name = param_info["name"]
                if param_name in flow["missing_params"]:
                    suggestions = suggest_parameter_values(param_name, resource_type, st.session_state.get('user_id', 'default_user'))
                    if suggestions:
                        suggestion_text = f"{param_info['prompt']}\nHere are some suggestions:\n" + "\n".join([f"- {sug}" for sug in suggestions])
                        st.session_state.messages.append({"role": "assistant", "content": suggestion_text})
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": param_info["prompt"]})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": param_info["prompt"]})
            else:
                st.session_state.messages.append({"role": "assistant", "content": param_info["prompt"]})

        flow["current_param_index"] = param_idx + 1
    else:
        # All parameters collected, show preview for confirmation
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
            session_id = st.session_state.get('session_id', 'default_session')
            diagnose_error(
                f"Error listing {resource_type}s",
                traceback.format_exc(),
                f"list_{resource_type}",
                {},
                session_id
            )
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
                    session_id = st.session_state.get('session_id', 'default_session')
                    diagnose_error(
                        f"Error destroying {resource_type.upper()}",
                        traceback.format_exc(),
                        f"destroy_{resource_type}",
                        {"resource_id": flow["selected_resource"].get(RESOURCE_DESTROY_IDS[resource_type])},
                        session_id
                    )
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

    # Handle confirmation step (same as create flow)
    if flow.get("awaiting_confirmation"):
        if user_message.lower() in ['yes', 'y', 'confirm', 'proceed']:
            flow["awaiting_confirmation"] = False
            flow["confirmed"] = True
            _execute_modify_resource(flow)
        elif user_message.lower() in ['modify', 'change', 'edit']:
            flow["awaiting_confirmation"] = False
            flow["awaiting_param_modification_decision"] = True
            st.session_state.messages.append({"role": "assistant", "content": "🔧 **Parameter Modification**\n\nWhich parameter would you like to change? You can specify:\n- Parameter name (e.g., 'instance type', 'volume size')\n- Or type 'list' to see all current parameters"})
        elif user_message.lower() in ['cancel', 'abort', 'no', 'n']:
            flow["active"] = False
            st.session_state.messages.append({"role": "assistant", "content": "❌ Resource modification cancelled."})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please respond with:\n- **'yes'** to proceed with modification\n- **'modify'** to change parameters\n- **'cancel'** to abort"})
        return

    # Handle parameter modification (same as create flow)
    if flow.get("awaiting_param_modification_decision"):
        if user_message.lower() in ['list', 'show', 'current']:
            # Show current parameters
            current_params = flow.get("params", {})
            if current_params:
                current_params_str = "\n".join([f"- **{k.replace('_', ' ').title()}:** {v}" for k, v in current_params.items()])
                st.session_state.messages.append({"role": "assistant", "content": f"📋 **Current Parameters:**\n{current_params_str}\n\nWhich parameter would you like to change?"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "No parameters set yet. Which parameter would you like to modify?"})
            return
        elif user_message.lower() in ['done', 'finished', 'proceed']:
            flow["awaiting_param_modification_decision"] = False
            _show_modify_preview(flow)  # Show preview again
            return
        else:
            # Try to match parameter
            param_to_modify = _find_parameter_by_input(user_message, resource_type, flow.get("params", {}))
            if param_to_modify:
                flow["param_to_modify"] = param_to_modify
                flow["awaiting_param_modification_decision"] = False
                flow["awaiting_new_param_value"] = True
                current_value = flow.get("params", {}).get(param_to_modify, "Not set")
                st.session_state.messages.append({"role": "assistant", "content": f"Current value for **{param_to_modify.replace('_', ' ').title()}**: {current_value}\n\nWhat is the new value?"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "❌ Parameter not found. Please specify a valid parameter name or type 'list' to see all parameters."})
            return

    if flow.get("awaiting_new_param_value"):
        param_to_modify = flow["param_to_modify"]
        flow["params"][param_to_modify] = user_message.strip()
        flow["awaiting_new_param_value"] = False
        flow["param_to_modify"] = None
        st.session_state.messages.append({"role": "assistant", "content": f"✅ Parameter updated! **{param_to_modify.replace('_', ' ').title()}** is now: {user_message.strip()}\n\nWould you like to modify another parameter? (yes/no)"})
        flow["awaiting_param_modification_decision"] = True
        return

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
                # Initialize params with current resource values for preview
                flow["params"] = _extract_current_resource_params(resources[0], resource_type)
                _show_modify_preview(flow)
                flow["awaiting_confirmation"] = True
            else:
                resource_list_str = f"Please select a {resource_type.upper()} to modify by number:\n"
                for i, resource in enumerate(resources):
                    resource_list_str += f"{i+1}. {resource[RESOURCE_IDENTIFIERS[resource_type]]}\n"
                st.session_state.messages.append({"role": "assistant", "content": resource_list_str})
                flow["awaiting_selection"] = True
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"Error listing {resource_type}s: {e}"})
            session_id = st.session_state.get('session_id', 'default_session')
            diagnose_error(
                f"Error listing {resource_type}s",
                traceback.format_exc(),
                f"list_{resource_type}",
                {},
                session_id
            )
            flow["active"] = False
        return

    # Stage 2: Handle user selection if multiple resources
    if flow.get("awaiting_selection"):
        selected_resource = _find_resource_by_identifier(user_message, flow["resources"], resource_type)

        if selected_resource:
            flow["selected_resource"] = selected_resource
            flow["resource_selected"] = True
            flow["awaiting_selection"] = False
            # Initialize params with current resource values for preview
            flow["params"] = _extract_current_resource_params(selected_resource, resource_type)
            _show_modify_preview(flow)
            flow["awaiting_confirmation"] = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Invalid selection. Please choose a number from the list, or provide the resource name or ID."})
        return

    # If we get here, something went wrong
    st.session_state.messages.append({"role": "assistant", "content": "❌ Unexpected state in modify flow. Please try again."})
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
            session_id = st.session_state.get('session_id', 'default_session')
            diagnose_error(
                f"Error listing {resource_type.upper()}: {e}",
                traceback.format_exc(),
                f"list_{resource_type}",
                {},
                session_id
            )
    if "conversation_flow" in st.session_state:
        st.session_state.conversation_flow["active"] = False



def handle_cost_estimation(user_message):
    st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you estimate the cost of your request."})
    session_id = st.session_state.get('session_id', 'default_session')
    try:
        recent_history = get_recent_history(session_id, limit=3)
        context_str = ""
        if recent_history:
            context_str = "Recent conversation context:\n" + "\n".join([f"- {msg.get('content', '')}" for msg in recent_history if msg.get('role') == 'user'])

        prompt = f"""Please estimate the monthly cost of the following AWS resource request.
        {context_str}
        Request: {user_message}

        Provide a detailed breakdown of the costs and any assumptions you made.
        Include cost-saving recommendations if applicable."""

        cost_estimation, _ = send_to_perplexity(prompt)
        st.session_state.messages.append({"role": "assistant", "content": cost_estimation})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error estimating cost: {e}"})
        diagnose_error(
            f"Error estimating cost: {e}",
            traceback.format_exc(),
            "cost_estimation",
            {},
            session_id
        )

def handle_list_creatable_resources():
    st.session_state.messages.append({"role": "assistant", "content": "Here are the AWS resources you can create:"})
    resource_list_str = ""
    for resource_type in RESOURCE_PARAMS.keys():
        resource_list_str += f"- {resource_type.replace('_', ' ').title()}\n"
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

def handle_enhanced_intent_recognition(user_message):
    """
    Enhanced intent recognition using AI-powered classification,
    context awareness, and proactive suggestions.
    """
    if not user_message:
        return

    session_id = st.session_state.get('session_id', 'default_session')
    user_id = st.session_state.get('user_id', 'default_user')

    # Get conversation context and history
    context = get_context(session_id, user_id)
    recent_history = get_recent_history(session_id, limit=5)

    # Use enhanced AI-powered intent classification
    intent, confidence, extracted_params = classify_intent(user_message, recent_history)

    # Update context with current intent and confidence
    update_context(session_id, current_intent=intent, confidence_score=confidence)

    # Handle different intent types
    if intent == 'unknown':
        # Provide suggestions for unclear intents
        suggestions = get_intent_suggestions(user_message)
        if suggestions:
            suggestion_text = "I'm not sure what you meant. Did you want to:\n" + "\n".join([f"- {sug}" for sug in suggestions])
            st.session_state.messages.append({"role": "assistant", "content": suggestion_text})
        else:
            # Fallback to general AI response
            ai_response, err = send_to_perplexity(user_message)
            if err:
                st.session_state.messages.append({"role": "assistant", "content": f"AI communication failed: {err}"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": ai_response})

    elif intent in ['create_ec2', 'create_s3', 'create_rds', 'create_dynamodb', 'create_iam_user', 'create_iam_role', 'create_iam_policy']:
        resource_type = intent.replace('create_', '')
        handle_enhanced_create_resource(user_message, resource_type, extracted_params, session_id, user_id)

    elif intent in ['destroy_ec2', 'destroy_s3', 'destroy_rds', 'destroy_dynamodb', 'destroy_iam_user', 'destroy_iam_role', 'destroy_iam_policy']:
        resource_type = intent.replace('destroy_', '')
        handle_enhanced_destroy_resource(user_message, resource_type, session_id)

    elif intent in ['list_ec2', 'list_s3', 'list_rds', 'list_dynamodb', 'list_iam_user', 'list_iam_role', 'list_iam_policy']:
        resource_type = intent.replace('list_', '')
        handle_list_resources(resource_type)

    elif intent in ['modify_ec2']:
        resource_type = intent.replace('modify_', '')
        handle_enhanced_modify_resource(user_message, resource_type, extracted_params, session_id)

    elif intent == 'cost_estimation':
        handle_enhanced_cost_estimation(user_message, session_id)

    elif intent == 'help':
        handle_enhanced_help(session_id)

    else:
        # Handle other intents or fallback to AI
        ai_response, err = send_to_perplexity(user_message)
        if err:
            st.session_state.messages.append({"role": "assistant", "content": f"AI communication failed: {err}"})
        else:
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

    # Add proactive suggestions if confidence is high enough
    if confidence > 0.7 and intent.startswith(('create_', 'destroy_')):
        suggestions = get_proactive_suggestions(intent, extracted_params or {}, user_id)
        if suggestions:
            suggestion_text = "\n💡 **Suggestions:**\n" + "\n".join([f"• {sug}" for sug in suggestions[:3]])
            st.session_state.messages.append({"role": "assistant", "content": suggestion_text})

def handle_enhanced_create_resource(user_message, resource_type, extracted_params, session_id, user_id):
    """
    Enhanced resource creation with smart parameter extraction and suggestions.
    """
    st.session_state.messages.append({"role": "assistant", "content": f"✅ I can help you create a {resource_type.upper()} resource."})

    # Extract parameters using enhanced extractor
    all_params = extract_parameters(user_message, resource_type, get_recent_history(session_id), user_id)

    # Merge with any previously extracted parameters
    if extracted_params:
        all_params.update(extracted_params)

    # Check for missing required parameters
    missing_params = get_missing_parameters(all_params, resource_type)

    if missing_params:
        st.session_state.messages.append({"role": "assistant", "content": f"📝 I found some parameters from your message, but I need a few more details to create the {resource_type.upper()}.\n\n**Missing Parameters:** {', '.join([p.replace('_', ' ').title() for p in missing_params])}"})

        # Find the index of the first missing parameter in the standard RESOURCE_PARAMS order
        params_for_resource = RESOURCE_PARAMS.get(resource_type, [])
        param_names = [p["name"] for p in params_for_resource]

        # Find the first missing parameter that exists in the standard order
        first_missing = None
        current_param_index = 0
        for i, param_name in enumerate(param_names):
            if param_name in missing_params:
                first_missing = param_name
                current_param_index = i
                break

        if first_missing:
            # Start conversation flow for missing parameters using standard flow
            st.session_state.conversation_flow = {
                "active": True,
                "type": "create_resource",
                "resource_type": resource_type,
                "params": all_params,
                "current_param_index": current_param_index,
                "missing_params": missing_params,
                "extracted_params": all_params,
                "enhanced_flow": True  # Mark this as coming from enhanced flow
            }

            # Don't ask for the parameter here - let the standard flow handle it
            # This prevents double-asking for the same parameter
            handle_create_resource_flow(None)
            return
        else:
            # Fallback if no missing parameters found in standard order
            st.session_state.messages.append({"role": "assistant", "content": "❌ I couldn't determine which parameter to ask for next. Please try using the standard creation flow."})
    else:
        # All parameters available, proceed with preview
        st.session_state.messages.append({"role": "assistant", "content": f"✅ Great! I have all the required parameters for creating the {resource_type.upper()}."})

        st.session_state.conversation_flow = {
            "active": True,
            "type": "create_resource",
            "resource_type": resource_type,
            "params": all_params,
            "current_param_index": len(RESOURCE_PARAMS.get(resource_type, [])),
            "ready_to_execute": True
        }
        handle_create_resource_flow(None)

def handle_enhanced_destroy_resource(user_message, resource_type, session_id):
    """
    Enhanced resource destruction with context awareness.
    Always shows the list of resources first for user selection.
    """
    st.session_state.messages.append({"role": "assistant", "content": f"Okay, I can help you destroy a {resource_type.upper()} resource."})

    # Always list resources for selection first, regardless of active context
    # This gives users full visibility and control over which resource to destroy
    st.session_state.conversation_flow = {
        "active": True,
        "type": "destroy_resource",
        "resource_type": resource_type,
    }
    handle_destroy_resource_flow(None)

def handle_enhanced_cost_estimation(user_message, session_id):
    """
    Enhanced cost estimation with context awareness.
    """
    st.session_state.messages.append({"role": "assistant", "content": "Okay, I can help you estimate the cost of your request."})

    # Get recent context to provide more accurate estimates
    recent_history = get_recent_history(session_id, limit=3)
    context_str = ""
    if recent_history:
        context_str = "Recent conversation context:\n" + "\n".join([f"- {msg.get('content', '')}" for msg in recent_history if msg.get('role') == 'user'])

    try:
        prompt = f"""Please estimate the monthly cost of the following AWS resource request.
        {context_str}
        Request: {user_message}

        Provide a detailed breakdown of the costs and any assumptions you made.
        Include cost-saving recommendations if applicable."""

        cost_estimation, _ = send_to_perplexity(prompt)
        st.session_state.messages.append({"role": "assistant", "content": cost_estimation})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error estimating cost: {e}"})
        diagnose_error(f"Error estimating cost: {e}", traceback.format_exc())

def handle_enhanced_modify_resource(user_message, resource_type, extracted_params, session_id):
    """
    Enhanced resource modification with smart parameter extraction and context awareness.
    """
    st.session_state.messages.append({"role": "assistant", "content": f"✅ I can help you modify a {resource_type.upper()} resource."})

    # Extract parameters using enhanced extractor
    all_params = extract_parameters(user_message, resource_type, get_recent_history(session_id), st.session_state.get('user_id', 'default_user'))

    # Merge with any previously extracted parameters
    if extracted_params:
        all_params.update(extracted_params)

    # For modify operations, we need to identify which parameter to modify
    # Look for specific modify patterns in the message
    modify_patterns = {
        'vol1_root_size': [
            r'\b(modify|change|update)\s+(root\s+)?disk\s+size\s+to\s+(\d+)\s*(gb|gigabytes?)',
            r'\b(modify|change|update)\s+(root\s+)?volume\s+size\s+to\s+(\d+)\s*(gb|gigabytes?)',
            r'\bset\s+(root\s+)?disk\s+size\s+to\s+(\d+)\s*(gb|gigabytes?)',
            r'\bset\s+(root\s+)?volume\s+size\s+to\s+(\d+)\s*(gb|gigabytes?)'
        ],
        'vol1_volume_type': [
            r'\b(modify|change|update)\s+(root\s+)?volume\s+type\s+to\s+(\w+)',
            r'\bset\s+(root\s+)?volume\s+type\s+to\s+(\w+)'
        ],
        'ec2_type': [
            r'\b(modify|change|update)\s+instance\s+type\s+to\s+([\w\.\-]+)',
            r'\bset\s+instance\s+type\s+to\s+([\w\.\-]+)'
        ]
    }

    # Try to identify the parameter to modify and its new value
    param_to_modify = None
    new_value = None

    message_lower = user_message.lower()
    for param, patterns in modify_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                param_to_modify = param
                # Extract the value (usually in the last group)
                if match.lastindex >= 2:
                    new_value = match.group(match.lastindex - 1)  # Usually the value is in the second-to-last group
                    if param in ['vol1_root_size'] and match.lastindex >= 3:
                        new_value = match.group(match.lastindex - 2)  # For size patterns, value is earlier
                break
        if param_to_modify:
            break

    # If we couldn't extract the parameter from patterns, try from all_params
    if not param_to_modify:
        # Check if any parameters were extracted that make sense for modification
        modifiable_params = ['vol1_root_size', 'vol1_volume_type', 'ec2_type']
        for param in modifiable_params:
            if param in all_params:
                param_to_modify = param
                new_value = all_params[param]
                break

    if not param_to_modify or not new_value:
        # If we can't determine what to modify, fall back to the standard modify flow
        st.session_state.messages.append({"role": "assistant", "content": f"I need more information to modify your {resource_type.upper()}. Let me show you your existing resources."})
        st.session_state.conversation_flow = {
            "active": True,
            "type": "modify_resource",
            "resource_type": resource_type,
        }
        handle_modify_resource_flow(None)
        return

    # We have the parameter and value, now find the resource to modify
    try:
        list_function = getattr(terraform_service, f"list_{resource_type}")
        resources = list_function()

        if not resources:
            st.session_state.messages.append({"role": "assistant", "content": f"No {resource_type.upper()} resources found to modify."})
            return

        if len(resources) == 1:
            # Only one resource, use it
            selected_resource = resources[0]
        else:
            # Multiple resources - require explicit user selection for safety
            resource_list_str = f"I found multiple {resource_type.upper()} resources. Please select which one to modify:\n"
            for i, resource in enumerate(resources):
                resource_list_str += f"{i+1}. {resource[RESOURCE_IDENTIFIERS[resource_type]]}\n"
            st.session_state.messages.append({"role": "assistant", "content": resource_list_str})

            # Set up flow to wait for user selection
            st.session_state.conversation_flow = {
                "active": True,
                "type": "modify_resource",
                "resource_type": resource_type,
                "resources": resources,
                "awaiting_selection": True,
                "param_to_modify": param_to_modify,
                "new_value": new_value
            }
            return

        # Get the instance ID
        instance_id = selected_resource[RESOURCE_DESTROY_IDS[resource_type]]

        # Execute the modification
        with st.spinner(f"Modifying {resource_type.upper()} {instance_id}..."):
            try:
                if param_to_modify == 'vol1_root_size':
                    response = terraform_service.update_ec2_volume_size(instance_id, new_value)
                else:
                    # For other parameters, we might need different functions
                    # For now, fall back to standard modify flow
                    st.session_state.messages.append({"role": "assistant", "content": f"Modifying {param_to_modify.replace('_', ' ').title()} is not yet supported through this enhanced flow. Let me use the standard modification process."})
                    st.session_state.conversation_flow = {
                        "active": True,
                        "type": "modify_resource",
                        "resource_type": resource_type,
                        "selected_resource": selected_resource,
                        "resource_selected": True,
                        "awaiting_param_selection": True
                    }
                    handle_modify_resource_flow(None)
                    return

                st.session_state.messages.append({"role": "assistant", "content": f"✅ {resource_type.upper()} modified successfully!\n\n**Parameter Updated:** {param_to_modify.replace('_', ' ').title()}\n**New Value:** {new_value}"})

                # Update context with the modification
                update_context(session_id, last_action=f"modified_{resource_type}", modified_param=param_to_modify)

            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"❌ Error modifying {resource_type.upper()}: {e}"})
                session_id = st.session_state.get('session_id', 'default_session')
                diagnose_error(
                    f"Error modifying {resource_type.upper()}",
                    traceback.format_exc(),
                    f"modify_{resource_type}",
                    {"param_to_modify": param_to_modify, "new_value": new_value},
                    session_id
                )

    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"Error accessing {resource_type.upper()} resources: {e}"})
        diagnose_error(
            f"Error listing {resource_type.upper()} for modification",
            traceback.format_exc(),
            f"list_{resource_type}",
            {},
            session_id
        )

def handle_enhanced_help(session_id):
    """
    Enhanced help with contextual suggestions.
    """
    context = get_context(session_id)
    current_state = context.conversation_state if hasattr(context, 'conversation_state') else 'idle'
    current_intent = context.current_intent if hasattr(context, 'current_intent') else ''

    help_messages = get_contextual_help(current_state, current_intent)

    help_text = "**Help & Guidance:**\n" + "\n".join([f"• {msg}" for msg in help_messages])

    # Add general help
    general_help = """
**Available Commands:**
• Create resources: "create an EC2 instance", "create an S3 bucket", etc.
• List resources: "list EC2 instances", "list S3 buckets", etc.
• Destroy resources: "destroy EC2 instance", "destroy S3 bucket", etc.
• Modify resources: "modify root disk size to 150gb", "change instance type", etc.
• Cost estimation: "what's the cost of..."
• Help: "help" or "what can you do"

**Tips:**
• You can specify multiple parameters in one message
• Use natural language like "powerful instance" or "small database"
• Type 'history' to see your command history"""

    st.session_state.messages.append({"role": "assistant", "content": help_text + general_help})

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
