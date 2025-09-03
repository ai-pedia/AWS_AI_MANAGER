import re
import json
from typing import Dict, List, Tuple, Optional, Any
from utils.ai_client import send_to_perplexity
from utils.context_manager import get_user_profile, get_smart_defaults

class ParameterExtractor:
    """
    Advanced parameter extraction system that can extract multiple parameters
    from natural language messages and handle ambiguous inputs intelligently.
    """

    def __init__(self):
        # Parameter patterns for different resource types
        self.parameter_patterns = {
            'ec2': {
                'ec2_name': [
                    r'\b(name|named|call)\s+(it|the instance)?\s*["\']?([^"\']+)["\']?',
                    r'\binstance\s+name[:\-]?\s*["\']?([^"\']+)["\']?'
                ],
                'ec2_ami': [
                    r'\bami[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\bami\s+id[:\-]?\s*["\']?([^"\']+)["\']?'
                ],
                'ec2_type': [
                    r'\b(instance\s+)?type[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(t2|t3|m5|m6|c5|r5|i3)\.(\w+)',
                    r'\b(micro|small|medium|large|xlarge|2xlarge|4xlarge|8xlarge|12xlarge|16xlarge|24xlarge)\b'
                ],
                'vol1_root_size': [
                    r'\b(root\s+)?volume[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bdisk[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bstorage[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\broot\s+disk\s+as\s+(\d+)\s*(gb|gigabytes?)',
                    r'\broot\s+disk[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'[,;]?\s*root\s+disk[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'[,;]?\s*root\s+volume[:\-]?\s*(\d+)\s*(gb|gigabytes?)'
                ],
                'vol1_volume_type': [
                    r'\bvolume\s+type[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(gp2|gp3|io1|io2|standard|st1|sc1)\b'
                ],
                'ec2_availabilityzone': [
                    r'\b(availability\s+)?zone[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(az|zone)[:\-]?\s*["\']?([^"\']+)["\']?'
                ],
                'ec2_ebs2_data_size': [
                    r'\bdata\s+(disk|volume)[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bdata\s+size[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bebs2[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bdata\s+disk\s+as\s+(\d+)\s*(gb|gigabytes?)',
                    r'\bdata\s+disk[:\-]?\s*(\d+)\s*(gb|gigabytes?)'
                ]
            },
            's3': {
                'bucket_name': [
                    r'\bbucket[:\-]?\s*(name)?[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(name|named|call)\s+(it|the bucket)?\s*["\']?([^"\']+)["\']?'
                ]
            },
            'rds': {
                'db_identifier': [
                    r'\b(identifier|id)[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(name|named|call)\s+(it|the database)?\s*["\']?([^"\']+)["\']?'
                ],
                'db_engine': [
                    r'\bengine[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(mysql|postgres|aurora|mariadb|oracle|sqlserver)\b'
                ],
                'db_engine_version': [
                    r'\bversion[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(\d+\.\d+|\d+\.\d+\.\d+)\b'
                ],
                'db_instance_class': [
                    r'\binstance\s+class[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(db\.(t2|t3|m5|m6|c5|r5))\.(\w+)\b'
                ],
                'allocated_storage': [
                    r'\b(storage|allocated)[:\-]?\s*(\d+)\s*(gb|gigabytes?)',
                    r'\bsize[:\-]?\s*(\d+)\s*(gb|gigabytes?)'
                ],
                'db_username': [
                    r'\b(username|user)[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\buser[:\-]?\s*["\']?([^"\']+)["\']?'
                ],
                'db_password': [
                    r'\bpassword[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\bpass[:\-]?\s*["\']?([^"\']+)["\']?'
                ]
            },
            'dynamodb': {
                'table_name': [
                    r'\btable[:\-]?\s*(name)?[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(name|named|call)\s+(it|the table)?\s*["\']?([^"\']+)["\']?'
                ],
                'hash_key_name': [
                    r'\bhash\s+key[:\-]?\s*(name)?[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\bprimary\s+key[:\-]?\s*(name)?[:\-]?\s*["\']?([^"\']+)["\']?'
                ],
                'hash_key_type': [
                    r'\bhash\s+key[:\-]?\s*type[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\bkey\s+type[:\-]?\s*["\']?([^"\']+)["\']?',
                    r'\b(S|N|B)\b'
                ]
            }
        }

        # Instance type mappings for intelligent suggestions
        self.instance_type_mappings = {
            'micro': 't3.micro',
            'small': 't3.small',
            'medium': 't3.medium',
            'large': 't3.large',
            'xlarge': 't3.xlarge',
            'powerful': 'm5.large',
            'high-memory': 'r5.large',
            'compute-optimized': 'c5.large',
            'storage-optimized': 'i3.large'
        }

        # Volume type mappings
        self.volume_type_mappings = {
            'ssd': 'gp3',
            'hdd': 'sc1',
            'magnetic': 'standard',
            'provisioned-iops': 'io1',
            'general-purpose': 'gp3'
        }

    def extract_parameters_regex(self, message: str, resource_type: str) -> Dict[str, Any]:
        """
        Extract parameters using regex patterns
        """
        extracted_params = {}
        message_lower = message.lower()

        if resource_type not in self.parameter_patterns:
            return extracted_params

        patterns = self.parameter_patterns[resource_type]

        for param_name, param_patterns in patterns.items():
            for pattern in param_patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    # Extract the captured group intelligently
                    value = self._extract_value_from_match(match, param_name)

                    # Clean up the value
                    value = self._clean_extracted_value(value)

                    if value:
                        extracted_params[param_name] = value
                        break  # Use first match for this parameter

        return extracted_params

    def _extract_value_from_match(self, match, param_name: str) -> str:
        """Extract the appropriate value from regex match groups"""
        if not match.lastindex:
            return match.group(0).strip()

        # For size parameters, prefer numeric values over units
        if param_name in ['vol1_root_size', 'allocated_storage', 'ec2_ebs2_data_size']:
            # Look for numeric groups first
            for i in range(1, match.lastindex + 1):
                group_value = match.group(i)
                if group_value and group_value.isdigit():
                    return group_value.strip()

        # For volume type parameters, return the matched volume type directly
        elif param_name == 'vol1_volume_type':
            # For volume type patterns like \b(gp2|gp3|io1|io2|standard|st1|sc1)\b
            # The match will be in group 1
            if match.lastindex >= 1:
                group_value = match.group(1)
                if group_value:
                    return group_value.strip()
            # Fallback to full match
            return match.group(0).strip()

        # For parameters with multiple groups, try to find the most relevant one
        # Skip common "noise" groups like units, prefixes
        units = ['gb', 'gigabytes', 'mb', 'megabytes', 'tb', 'terabytes']
        prefixes = ['root', 'data', 'storage', 'volume', 'disk', 'size']

        for i in range(match.lastindex, 0, -1):
            group_value = match.group(i)
            if group_value:
                group_lower = group_value.lower().strip()
                if group_lower not in units and group_lower not in prefixes:
                    return group_value.strip()

        # Fallback to last group
        return match.group(match.lastindex).strip()

    def extract_parameters_ai(self, message: str, resource_type: str, context: List[Dict] = None) -> Tuple[Dict[str, Any], float]:
        """
        Extract parameters using AI analysis
        Returns: (parameters_dict, confidence_score)
        """
        context_str = ""
        if context and len(context) > 0:
            recent_messages = context[-3:]
            context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_messages])

        # Define expected parameters for the resource type
        expected_params = {}
        if resource_type in self.parameter_patterns:
            for param_name in self.parameter_patterns[resource_type].keys():
                expected_params[param_name] = f"Parameter for {param_name.replace('_', ' ')}"

        prompt = f"""
        Extract AWS resource parameters from the user's message for creating a {resource_type.upper()} resource.
        Consider the conversation context if provided.

        Conversation Context:
        {context_str}

        User Message: {message}

        Expected Parameters for {resource_type.upper()}:
        {json.dumps(expected_params, indent=2)}

        Common AWS values to recognize:
        - Instance types: t3.micro, t3.small, t3.medium, m5.large, c5.xlarge, etc.
        - Volume types: gp2, gp3, io1, st1, sc1
        - Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-1, etc.
        - Availability Zones: us-east-1a, us-east-1b, us-east-1c, us-west-2a, etc.
        - Database engines: mysql, postgres, aurora, mariadb
        - Key types: S (String), N (Number), B (Binary)

        CRITICAL COST-SAFETY RULES - NEVER INFER THESE PARAMETERS:
        """

        # Add resource-specific cost warnings
        if resource_type == 'ec2':
            prompt += """
        EC2 COST PARAMETERS (always ask user):
        - vol1_volume_type: gp2 vs gp3 have significantly different costs
        - ec2_availabilityzone: Different regions/zones have different pricing
        - vol1_root_size: Storage size directly affects cost
        - ec2_ebs2_data_size: Additional storage costs money
        """
        elif resource_type == 'rds':
            prompt += """
        RDS COST PARAMETERS (always ask user):
        - allocated_storage: Database storage size directly affects cost
        - db_instance_class: Instance type determines compute costs
        - db_engine: Some engines (Aurora) are more expensive than others
        - db_engine_version: Newer versions may have different pricing
        """
        elif resource_type == 's3':
            prompt += """
        S3 COST PARAMETERS (always ask user):
        - bucket_name: Must be globally unique (not cost-related but required)
        """
        elif resource_type == 'dynamodb':
            prompt += """
        DYNAMODB COST PARAMETERS (always ask user):
        - table_name: Required for table creation
        - hash_key_name: Required for table schema
        - hash_key_type: Required for table schema
        """

        prompt += f"""

        GENERAL RULE: Only extract parameters that are EXPLICITLY mentioned in the user's message.
        DO NOT make assumptions about missing parameters, especially cost-related ones.
        Only infer if it's absolutely clear from the message or previous context.

        Return your response in this exact JSON format:
        {{
            "parameters": {{
                "parameter_name": "extracted_value"
            }},
            "confidence": 0.85,
            "reasoning": "Brief explanation of extraction logic"
        }}

        Only include parameters that are clearly mentioned in the user's message.
        Let the conversation system handle asking for missing parameters to avoid unexpected costs.
        """

        try:
            response, error = send_to_perplexity(prompt)
            if error:
                return {}, 0.0

            # Parse JSON response
            try:
                result = json.loads(response.strip())
                parameters = result.get('parameters', {})
                confidence = result.get('confidence', 0.5)

                # Validate and clean parameters
                validated_params = self._validate_parameters(parameters, resource_type)

                return validated_params, confidence
            except json.JSONDecodeError:
                # Fallback: try to extract from text
                return self._extract_from_text_response(response, resource_type), 0.3

        except Exception as e:
            print(f"AI parameter extraction error: {e}")
            return {}, 0.0

    def _extract_from_text_response(self, response: str, resource_type: str) -> Dict[str, Any]:
        """Fallback parameter extraction from text response"""
        extracted = {}
        response_lower = response.lower()

        # Simple pattern matching for common parameters
        if resource_type == 'ec2':
            # Look for instance type patterns
            instance_match = re.search(r'(t2|t3|m5|c5|r5)\.(micro|small|medium|large|xlarge)', response_lower)
            if instance_match:
                extracted['ec2_type'] = instance_match.group(0)

        return extracted

    def extract_parameters_hybrid(self, message: str, resource_type: str,
                                context: List[Dict] = None, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Hybrid parameter extraction combining regex and AI approaches
        """
        # Start with regex extraction (fast and reliable)
        regex_params = self.extract_parameters_regex(message, resource_type)

        # Use AI for additional extraction and validation
        ai_params, ai_confidence = self.extract_parameters_ai(message, resource_type, context)

        # Merge parameters with priority to AI when confidence is high
        final_params = regex_params.copy()

        if ai_confidence > 0.7:
            final_params.update(ai_params)
        else:
            # For lower confidence, only add AI params that don't conflict with regex
            for key, value in ai_params.items():
                if key not in final_params:
                    final_params[key] = value

        # Apply intelligent mappings and defaults
        final_params = self._apply_intelligent_mappings(final_params, resource_type)

        # Add smart defaults based on user history
        smart_defaults = get_smart_defaults(user_id, f"create_{resource_type}")
        for key, value in smart_defaults.items():
            if key not in final_params:
                final_params[key] = value

        return final_params

    def _apply_intelligent_mappings(self, params: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
        """Apply intelligent mappings for ambiguous values"""
        mapped_params = params.copy()

        # Instance type mappings
        if 'ec2_type' in mapped_params:
            instance_type = mapped_params['ec2_type'].lower()
            if instance_type in self.instance_type_mappings:
                mapped_params['ec2_type'] = self.instance_type_mappings[instance_type]

        # Volume type mappings
        if 'vol1_volume_type' in mapped_params:
            volume_type = mapped_params['vol1_volume_type'].lower()
            if volume_type in self.volume_type_mappings:
                mapped_params['vol1_volume_type'] = self.volume_type_mappings[volume_type]

        # Don't apply defaults for required parameters - let the conversation flow handle them
        # This ensures users are always asked for required parameters with appropriate suggestions
        # Only apply defaults for truly optional parameters that don't affect the core functionality

        return mapped_params

    def _clean_extracted_value(self, value: str) -> str:
        """Clean and normalize extracted values"""
        if not value:
            return ""

        # Remove quotes
        value = value.strip('"\'')

        # Normalize whitespace
        value = ' '.join(value.split())

        # Convert to lowercase for consistency (except for names/identifiers)
        if not any(keyword in value.lower() for keyword in ['name', 'id', 'identifier']):
            value = value.lower()

        return value

    def _validate_parameters(self, params: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
        """Validate extracted parameters"""
        validated = {}

        for key, value in params.items():
            if not isinstance(value, str):
                validated[key] = str(value)
            else:
                validated[key] = value.strip()

        return validated

    def get_missing_parameters(self, extracted_params: Dict[str, Any], resource_type: str) -> List[str]:
        """Get list of missing required parameters"""
        if resource_type not in self.parameter_patterns:
            return []

        required_params = []
        patterns = self.parameter_patterns[resource_type]

        # Define which parameters are required for each resource type
        required_mapping = {
            'ec2': ['ec2_name', 'ec2_ami', 'ec2_type', 'vol1_volume_type', 'ec2_availabilityzone'],
            's3': ['bucket_name'],
            'rds': ['db_identifier', 'db_engine', 'db_engine_version', 'db_instance_class', 'allocated_storage', 'db_username', 'db_password'],
            'dynamodb': ['table_name', 'hash_key_name', 'hash_key_type']
        }

        if resource_type in required_mapping:
            required_params = required_mapping[resource_type]

        missing = []
        for param in required_params:
            if param not in extracted_params or not extracted_params[param]:
                missing.append(param)

        return missing

    def suggest_parameter_values(self, param_name: str, resource_type: str, user_id: str = "default_user") -> List[str]:
        """Suggest values for a parameter based on user history and best practices"""
        suggestions = []

        # Get user profile for personalized suggestions
        try:
            profile = get_user_profile(user_id)
        except:
            profile = None

        if param_name == 'ec2_name':
            # Suggest based on user history or common patterns
            if profile and hasattr(profile, 'common_instance_names'):
                suggestions.extend(profile.common_instance_names[-3:])
            suggestions.extend(['my-instance', 'web-server', 'app-server', 'test-instance'])

        elif param_name == 'ec2_ami':
            suggestions.extend(['ami-0abcdef1234567890', 'ami-0c55b159cbfafe1d0', 'ami-0c02fb55956c7d316'])

        elif param_name == 'ec2_type':
            # Suggest based on user history
            if profile and hasattr(profile, 'common_instance_types'):
                suggestions.extend(profile.common_instance_types[-3:])  # Last 3 used

            # Add popular defaults
            suggestions.extend(['t3.micro', 't3.small', 't3.medium', 'm5.large'])

        elif param_name == 'vol1_volume_type':
            suggestions.extend(['gp3', 'gp2', 'io1', 'st1', 'sc1'])

        elif param_name == 'bucket_name':
            # Suggest based on user history or common patterns
            if profile and hasattr(profile, 'common_bucket_names'):
                suggestions.extend(profile.common_bucket_names[-3:])
            suggestions.extend(['my-bucket', 'data-storage', 'backup-bucket', 'static-assets'])

        elif param_name == 'db_identifier':
            # Suggest based on user history or common patterns
            if profile and hasattr(profile, 'common_db_identifiers'):
                suggestions.extend(profile.common_db_identifiers[-3:])
            suggestions.extend(['my-database', 'prod-db', 'test-db', 'app-database'])

        elif param_name == 'db_engine':
            suggestions.extend(['postgres', 'mysql', 'aurora'])

        elif param_name == 'db_engine_version':
            # Suggest common versions based on the engine if available
            # For now, provide general suggestions
            suggestions.extend(['15.3', '14.5', '13.4', '8.0.28', '5.7.34'])

        elif param_name == 'db_instance_class':
            suggestions.extend(['db.t3.micro', 'db.t3.small', 'db.t3.medium'])

        elif param_name == 'allocated_storage':
            suggestions.extend(['20', '50', '100', '200', '500'])

        elif param_name == 'db_username':
            suggestions.extend(['admin', 'postgres', 'root', 'dbuser'])

        elif param_name == 'db_password':
            suggestions.extend(['ChangeMe123!', 'SecurePass2024!', 'MyDBPass123!'])

        elif param_name == 'table_name':
            # Suggest based on user history or common patterns
            if profile and hasattr(profile, 'common_table_names'):
                suggestions.extend(profile.common_table_names[-3:])
            suggestions.extend(['users', 'products', 'orders', 'items', 'data'])

        elif param_name == 'hash_key_name':
            suggestions.extend(['id', 'pk', 'user_id', 'item_id', 'primary_key'])

        elif param_name == 'hash_key_type':
            suggestions.extend(['S', 'N', 'B'])

        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for item in suggestions:
            if item not in seen:
                unique_suggestions.append(item)
                seen.add(item)

        return unique_suggestions[:5]  # Return up to 5 suggestions

# Global instance for easy access
parameter_extractor = ParameterExtractor()

def extract_parameters(message: str, resource_type: str, context: List[Dict] = None, user_id: str = "default_user") -> Dict[str, Any]:
    """Extract parameters from message"""
    return parameter_extractor.extract_parameters_hybrid(message, resource_type, context, user_id)

def get_missing_parameters(extracted_params: Dict[str, Any], resource_type: str) -> List[str]:
    """Get missing required parameters"""
    return parameter_extractor.get_missing_parameters(extracted_params, resource_type)

def suggest_parameter_values(param_name: str, resource_type: str, user_id: str = "default_user") -> List[str]:
    """Get parameter value suggestions"""
    return parameter_extractor.suggest_parameter_values(param_name, resource_type, user_id)
