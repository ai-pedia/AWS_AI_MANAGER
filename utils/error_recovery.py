import re
import traceback
from typing import Dict, List, Tuple, Optional, Any
from utils.ai_client import send_to_perplexity
from utils.suggestion_engine import get_contextual_help

class ErrorRecoveryEngine:
    """
    Intelligent error recovery system that analyzes errors, provides root cause analysis,
    and suggests automated recovery strategies.
    """

    def __init__(self):
        # Error pattern recognition
        self.error_patterns = {
            'credentials': [
                r'InvalidAccessKeyId',
                r'InvalidClientTokenId',
                r'InvalidToken',
                r'ExpiredToken',
                r'Unable to locate credentials',
                r'No credentials found'
            ],
            'permissions': [
                r'AccessDenied',
                r'UnauthorizedOperation',
                r'Forbidden',
                r'User.*is not authorized',
                r'permission.*denied'
            ],
            'resource_limits': [
                r'LimitExceeded',
                r'InsufficientCapacity',
                r'InstanceLimitExceeded',
                r'VolumeLimitExceeded',
                r'StorageQuotaExceeded'
            ],
            'resource_not_found': [
                r'ResourceNotFound',
                r'InvalidInstanceId',
                r'InvalidBucketName',
                r'DBInstanceNotFoundFault',
                r'TableNotFoundException'
            ],
            'parameter_validation': [
                r'InvalidParameterValue',
                r'InvalidParameterCombination',
                r'ValidationError',
                r'MissingParameter',
                r'InvalidAMIID'
            ],
            'networking': [
                r'InvalidSubnet',
                r'InvalidSecurityGroupId',
                r'InvalidVpcId',
                r'NetworkError'
            ],
            'service_unavailable': [
                r'ServiceUnavailable',
                r'Throttling',
                r'RateLimitExceeded',
                r'InternalError'
            ]
        }

        # Recovery strategies for each error type
        self.recovery_strategies = {
            'credentials': [
                "Check your AWS access key and secret key",
                "Verify your credentials are not expired",
                "Ensure you're using the correct AWS region",
                "Try refreshing your AWS session token"
            ],
            'permissions': [
                "Review your IAM user permissions",
                "Check if required policies are attached",
                "Verify resource-level permissions",
                "Consider using a different IAM user with proper permissions"
            ],
            'resource_limits': [
                "Check your AWS service limits and quotas",
                "Request limit increases if necessary",
                "Try a different instance type or region",
                "Consider using reserved instances for better limits"
            ],
            'resource_not_found': [
                "Verify the resource ID or name is correct",
                "Check if the resource exists in the current region",
                "Ensure you're using the correct resource identifier format",
                "List available resources to verify names/IDs"
            ],
            'parameter_validation': [
                "Review parameter values and formats",
                "Check AWS documentation for valid parameter combinations",
                "Use default values for complex parameters",
                "Try simpler parameter values first"
            ],
            'networking': [
                "Verify VPC, subnet, and security group configurations",
                "Check network ACLs and route tables",
                "Ensure proper security group rules",
                "Try using default VPC settings"
            ],
            'service_unavailable': [
                "Wait a few minutes and retry the operation",
                "Try the operation in a different region",
                "Check AWS service status page for outages",
                "Consider using a different availability zone"
            ]
        }

    def analyze_error(self, error_message: str, traceback_str: str = "",
                     intent: str = "", parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze error and provide comprehensive recovery information
        """
        error_analysis = {
            'error_type': 'unknown',
            'severity': 'medium',
            'root_cause': '',
            'recovery_steps': [],
            'preventive_measures': [],
            'confidence': 0.0,
            'ai_analysis': {}
        }

        # Classify error type
        error_type = self._classify_error_type(error_message)
        error_analysis['error_type'] = error_type

        # Set severity based on error type
        error_analysis['severity'] = self._determine_severity(error_type)

        # Get basic recovery steps
        if error_type in self.recovery_strategies:
            error_analysis['recovery_steps'] = self.recovery_strategies[error_type][:3]

        # Get AI-powered analysis
        ai_analysis = self._get_ai_error_analysis(error_message, traceback_str, intent, parameters)
        if ai_analysis:
            error_analysis['ai_analysis'] = ai_analysis
            error_analysis['root_cause'] = ai_analysis.get('root_cause', '')
            error_analysis['confidence'] = ai_analysis.get('confidence', 0.5)

            # Add AI-suggested recovery steps
            ai_steps = ai_analysis.get('recovery_steps', [])
            if ai_steps:
                error_analysis['recovery_steps'].extend(ai_steps[:2])

        # Add preventive measures
        error_analysis['preventive_measures'] = self._get_preventive_measures(error_type, intent)

        return error_analysis

    def _classify_error_type(self, error_message: str) -> str:
        """Classify error type based on message patterns"""
        message_lower = error_message.lower()

        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return error_type

        return 'unknown'

    def _determine_severity(self, error_type: str) -> str:
        """Determine error severity"""
        severity_map = {
            'credentials': 'high',
            'permissions': 'high',
            'resource_limits': 'medium',
            'resource_not_found': 'low',
            'parameter_validation': 'medium',
            'networking': 'medium',
            'service_unavailable': 'low',
            'unknown': 'medium'
        }
        return severity_map.get(error_type, 'medium')

    def _get_ai_error_analysis(self, error_message: str, traceback_str: str = "",
                              intent: str = "", parameters: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get AI-powered error analysis"""
        parameters_str = ""
        if parameters:
            parameters_str = "\n".join([f"- {k}: {v}" for k, v in parameters.items()])

        prompt = f"""
        Analyze this AWS error and provide a detailed diagnosis with recovery steps.

        Error Message: {error_message}
        Traceback: {traceback_str}
        User Intent: {intent}
        Parameters Used: {parameters_str}

        Provide your analysis in this JSON format:
        {{
            "root_cause": "Brief explanation of the root cause",
            "confidence": 0.85,
            "recovery_steps": [
                "Step 1: Specific action to take",
                "Step 2: Another specific action",
                "Step 3: Final verification step"
            ],
            "alternative_solutions": [
                "Alternative 1: Different approach",
                "Alternative 2: Workaround solution"
            ],
            "preventive_measures": [
                "Prevention 1: How to avoid this error",
                "Prevention 2: Best practice recommendation"
            ]
        }}

        Focus on actionable advice specific to AWS services and the error context.
        """

        try:
            response, error = send_to_perplexity(prompt)
            if error:
                return None

            # Parse JSON response
            try:
                analysis = eval(response.strip())  # Simple JSON parsing for now
                if isinstance(analysis, dict):
                    return analysis
            except:
                # Fallback: extract information from text
                return self._parse_text_analysis(response)

        except Exception as e:
            print(f"AI error analysis failed: {e}")

        return None

    def _parse_text_analysis(self, response: str) -> Dict[str, Any]:
        """Parse text-based AI response"""
        analysis = {
            'root_cause': 'Error analysis unavailable',
            'confidence': 0.3,
            'recovery_steps': [],
            'alternative_solutions': [],
            'preventive_measures': []
        }

        # Simple text parsing
        lines = response.strip().split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'root cause' in line.lower():
                current_section = 'root_cause'
                analysis['root_cause'] = line.split(':', 1)[-1].strip()
            elif 'recovery' in line.lower() or 'step' in line.lower():
                current_section = 'recovery_steps'
                if line not in analysis['recovery_steps']:
                    analysis['recovery_steps'].append(line)
            elif 'alternative' in line.lower():
                current_section = 'alternative_solutions'
                if line not in analysis['alternative_solutions']:
                    analysis['alternative_solutions'].append(line)
            elif 'prevent' in line.lower():
                current_section = 'preventive_measures'
                if line not in analysis['preventive_measures']:
                    analysis['preventive_measures'].append(line)

        return analysis

    def _get_preventive_measures(self, error_type: str, intent: str) -> List[str]:
        """Get preventive measures for error type"""
        preventive_measures = []

        if error_type == 'credentials':
            preventive_measures.extend([
                "Use IAM roles instead of long-term access keys",
                "Implement credential rotation policies",
                "Use AWS SSO for better credential management"
            ])

        elif error_type == 'permissions':
            preventive_measures.extend([
                "Follow principle of least privilege",
                "Regular review of IAM policies and permissions",
                "Use policy simulators to test permissions"
            ])

        elif error_type == 'parameter_validation':
            preventive_measures.extend([
                "Validate parameters before making API calls",
                "Use AWS SDK parameter validation",
                "Keep up-to-date with AWS service limits and requirements"
            ])

        elif error_type == 'resource_limits':
            preventive_measures.extend([
                "Monitor AWS service usage and limits",
                "Implement automated cleanup of unused resources",
                "Use AWS Budgets and Cost Explorer for planning"
            ])

        # Intent-specific preventive measures
        if intent.startswith('create_'):
            preventive_measures.append("Test resource creation in development environment first")
        elif intent.startswith('destroy_'):
            preventive_measures.append("Always backup important data before destruction")

        return preventive_measures[:3]

    def suggest_parameter_modifications(self, error_message: str, original_params: Dict[str, Any],
                                      intent: str) -> List[Dict[str, Any]]:
        """
        Suggest parameter modifications to resolve errors
        """
        suggestions = []

        error_type = self._classify_error_type(error_message)
        resource_type = intent.replace('create_', '').replace('destroy_', '').replace('modify_', '')

        if error_type == 'parameter_validation':
            if resource_type == 'ec2':
                # Suggest alternative instance types
                current_type = original_params.get('ec2_type', '')
                if 't2' in current_type:
                    suggestions.append({
                        'parameter': 'ec2_type',
                        'suggested_value': current_type.replace('t2', 't3'),
                        'reason': 'T3 instances offer better performance and are more widely available'
                    })

            elif resource_type == 'rds':
                # Suggest smaller storage or different instance class
                storage = original_params.get('allocated_storage')
                if storage and int(storage) > 100:
                    suggestions.append({
                        'parameter': 'allocated_storage',
                        'suggested_value': '20',
                        'reason': 'Start with smaller storage and scale up as needed'
                    })

        elif error_type == 'resource_limits':
            if resource_type == 'ec2':
                suggestions.append({
                    'parameter': 'ec2_type',
                    'suggested_value': 't3.micro',
                    'reason': 'Use smaller instance type to avoid limits'
                })

        return suggestions

    def get_error_context_help(self, error_analysis: Dict[str, Any]) -> List[str]:
        """Get contextual help based on error analysis"""
        help_messages = []

        error_type = error_analysis.get('error_type', 'unknown')
        severity = error_analysis.get('severity', 'medium')

        if severity == 'high':
            help_messages.append("🚨 This appears to be a critical error. Please review the suggestions carefully.")
        elif severity == 'medium':
            help_messages.append("⚠️ This error may require parameter adjustments or permission changes.")
        else:
            help_messages.append("ℹ️ This is likely a minor configuration issue.")

        # Add specific help based on error type
        if error_type == 'credentials':
            help_messages.extend([
                "Try running 'aws configure' to update your credentials",
                "Check if your AWS session has expired"
            ])

        elif error_type == 'permissions':
            help_messages.extend([
                "Verify your IAM user has the required permissions",
                "Check the AWS IAM policy simulator for permission issues"
            ])

        elif error_type == 'parameter_validation':
            help_messages.extend([
                "Review AWS documentation for valid parameter combinations",
                "Try using default values for complex parameters"
            ])

        return help_messages

    def generate_error_report(self, error_message: str, traceback_str: str,
                            intent: str, parameters: Dict[str, Any]) -> str:
        """Generate a comprehensive error report"""
        analysis = self.analyze_error(error_message, traceback_str, intent, parameters)

        report = f"""
🔍 **Error Analysis Report**

**Error Type:** {analysis['error_type'].title()}
**Severity:** {analysis['severity'].title()}
**Confidence:** {analysis['confidence']:.1%}

**Root Cause:**
{analysis.get('root_cause', 'Unable to determine root cause')}

**Recovery Steps:**
"""

        for i, step in enumerate(analysis['recovery_steps'], 1):
            report += f"{i}. {step}\n"

        if analysis['preventive_measures']:
            report += "\n**Preventive Measures:**\n"
            for measure in analysis['preventive_measures']:
                report += f"• {measure}\n"

        if analysis['ai_analysis'].get('alternative_solutions'):
            report += "\n**Alternative Solutions:**\n"
            for alt in analysis['ai_analysis']['alternative_solutions']:
                report += f"• {alt}\n"

        return report.strip()

# Global instance for easy access
error_recovery_engine = ErrorRecoveryEngine()

def analyze_error(error_message: str, traceback_str: str = "",
                 intent: str = "", parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze error and provide recovery information"""
    return error_recovery_engine.analyze_error(error_message, traceback_str, intent, parameters)

def suggest_parameter_modifications(error_message: str, original_params: Dict[str, Any],
                                  intent: str) -> List[Dict[str, Any]]:
    """Suggest parameter modifications for error recovery"""
    return error_recovery_engine.suggest_parameter_modifications(error_message, original_params, intent)

def get_error_context_help(error_analysis: Dict[str, Any]) -> List[str]:
    """Get contextual help for error situation"""
    return error_recovery_engine.get_error_context_help(error_analysis)

def generate_error_report(error_message: str, traceback_str: str,
                        intent: str, parameters: Dict[str, Any]) -> str:
    """Generate comprehensive error report"""
    return error_recovery_engine.generate_error_report(error_message, traceback_str, intent, parameters)
