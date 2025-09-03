import re
from typing import Dict, List, Optional, Any
from utils.ai_client import send_to_perplexity
from utils.context_manager import get_user_profile, get_contextual_suggestions

class SuggestionEngine:
    """
    Intelligent suggestion engine that provides proactive recommendations,
    cost optimizations, security best practices, and contextual assistance.
    """

    def __init__(self):
        # Cost optimization suggestions
        self.cost_suggestions = {
            'ec2': [
                "Consider using spot instances for non-critical workloads to save up to 90%",
                "Use reserved instances for steady-state workloads to save up to 75%",
                "Right-size your instances based on actual usage patterns",
                "Consider Graviton-based instances for better price-performance ratio"
            ],
            'rds': [
                "Use Aurora Serverless for variable workloads to optimize costs",
                "Consider reserved DB instances for predictable usage",
                "Enable storage autoscaling to avoid over-provisioning",
                "Use Multi-AZ deployment only when necessary for high availability"
            ],
            's3': [
                "Use S3 Intelligent-Tiering for automatic cost optimization",
                "Configure lifecycle policies to move data to cheaper storage classes",
                "Use S3 Glacier for long-term archival storage",
                "Enable compression for frequently accessed data"
            ]
        }

        # Security suggestions
        self.security_suggestions = {
            'ec2': [
                "Use security groups with least privilege principle",
                "Enable AWS Config and CloudTrail for monitoring",
                "Regularly update AMIs with latest security patches",
                "Use IAM roles instead of access keys for EC2 instances"
            ],
            'rds': [
                "Place RDS instances in private subnets",
                "Use encrypted connections and enable encryption at rest",
                "Implement proper backup and retention policies",
                "Use IAM authentication instead of database passwords"
            ],
            's3': [
                "Enable versioning to protect against accidental deletion",
                "Use bucket policies and IAM policies for access control",
                "Enable server-side encryption for all objects",
                "Configure proper CORS settings for web applications"
            ]
        }

        # Performance suggestions
        self.performance_suggestions = {
            'ec2': [
                "Use instance types with NVMe storage for high I/O workloads",
                "Consider placement groups for low-latency requirements",
                "Use Elastic Load Balancing for high availability",
                "Implement auto-scaling groups for variable workloads"
            ],
            'rds': [
                "Use read replicas to offload read traffic",
                "Choose appropriate instance types based on workload characteristics",
                "Enable performance insights for monitoring",
                "Use connection pooling to optimize database connections"
            ]
        }

    def get_proactive_suggestions(self, intent: str, parameters: Dict[str, Any],
                                user_id: str = "default_user") -> List[str]:
        """
        Get proactive suggestions based on intent and parameters
        """
        suggestions = []

        # Get resource type from intent
        resource_type = intent.replace('create_', '').replace('destroy_', '').replace('modify_', '')

        # Cost optimization suggestions
        if intent.startswith('create_') and resource_type in self.cost_suggestions:
            cost_sug = self._get_relevant_cost_suggestions(resource_type, parameters)
            suggestions.extend(cost_sug)

        # Security suggestions
        if intent.startswith('create_') and resource_type in self.security_suggestions:
            security_sug = self._get_relevant_security_suggestions(resource_type, parameters)
            suggestions.extend(security_sug)

        # Performance suggestions
        if intent.startswith('create_') and resource_type in self.performance_suggestions:
            perf_sug = self._get_relevant_performance_suggestions(resource_type, parameters)
            suggestions.extend(perf_sug)

        # User-specific suggestions based on history
        user_suggestions = self._get_user_based_suggestions(user_id, intent, parameters)
        suggestions.extend(user_suggestions)

        # Parameter-specific suggestions
        param_suggestions = self._get_parameter_based_suggestions(intent, parameters)
        suggestions.extend(param_suggestions)

        return suggestions[:5]  # Return top 5 suggestions

    def _get_relevant_cost_suggestions(self, resource_type: str, parameters: Dict[str, Any]) -> List[str]:
        """Get cost optimization suggestions based on parameters"""
        suggestions = []

        if resource_type == 'ec2':
            instance_type = parameters.get('ec2_type', '').lower()
            if 't2' in instance_type:
                suggestions.append("Consider upgrading to T3 instances for better performance at similar cost")
            elif 'm5' in instance_type:
                suggestions.append("T3 instances might be more cost-effective for general workloads")

        elif resource_type == 'rds':
            storage = parameters.get('allocated_storage')
            if storage and int(storage) > 100:
                suggestions.append("Large storage amounts may benefit from Aurora's cost-effective scaling")

        return suggestions

    def _get_relevant_security_suggestions(self, resource_type: str, parameters: Dict[str, Any]) -> List[str]:
        """Get security suggestions based on parameters"""
        suggestions = []

        if resource_type == 'rds':
            publicly_accessible = parameters.get('db_publicly_accessible', '').lower()
            if publicly_accessible in ['yes', 'true', '1']:
                suggestions.append("⚠️ WARNING: Public RDS access is not recommended for production")
                suggestions.append("Consider placing RDS in private subnets with proper security groups")

        elif resource_type == 'ec2':
            # Check if security groups are mentioned
            if not any('security' in str(v).lower() for v in parameters.values()):
                suggestions.append("Consider configuring security groups for your EC2 instance")

        return suggestions

    def _get_relevant_performance_suggestions(self, resource_type: str, parameters: Dict[str, Any]) -> List[str]:
        """Get performance suggestions based on parameters"""
        suggestions = []

        if resource_type == 'ec2':
            instance_type = parameters.get('ec2_type', '').lower()
            volume_size = parameters.get('vol1_root_size')

            if volume_size and int(volume_size) > 100:
                suggestions.append("Large root volumes may benefit from GP3 for better performance")

            if 't2' in instance_type or 't3' in instance_type:
                suggestions.append("Consider burstable instances for variable workloads")

        return suggestions

    def _get_user_based_suggestions(self, user_id: str, intent: str, parameters: Dict[str, Any]) -> List[str]:
        """Get suggestions based on user history and preferences"""
        suggestions = []

        try:
            profile = get_user_profile(user_id)

            # Check usage patterns
            if hasattr(profile, 'usage_patterns') and intent in profile.usage_patterns:
                usage_count = profile.usage_patterns[intent]['count']
                if usage_count > 5:
                    suggestions.append(f"You've {intent.replace('_', ' ')} {usage_count} times. Consider automation!")

            # Region consistency
            if hasattr(profile, 'preferred_region'):
                current_region = parameters.get('region') or parameters.get('ec2_availabilityzone', '').split('-')[0:2]
                if isinstance(current_region, list):
                    current_region = '-'.join(current_region)
                if current_region and current_region != profile.preferred_region:
                    suggestions.append(f"You usually work in {profile.preferred_region}. Switch regions?")

        except Exception as e:
            print(f"Error getting user suggestions: {e}")

        return suggestions

    def _get_parameter_based_suggestions(self, intent: str, parameters: Dict[str, Any]) -> List[str]:
        """Get suggestions based on specific parameter values"""
        suggestions = []

        # EC2-specific suggestions
        if intent == 'create_ec2':
            instance_type = parameters.get('ec2_type', '')

            # Instance type specific suggestions
            if 't3.micro' in instance_type:
                suggestions.append("T3.micro is great for testing, but consider T3.small for light production")
            elif 'm5.large' in instance_type:
                suggestions.append("M5.large offers good balance of compute and cost")

            # Volume suggestions
            volume_size = parameters.get('vol1_root_size')
            if volume_size:
                try:
                    size_gb = int(volume_size)
                    if size_gb < 8:
                        suggestions.append("Minimum 8GB recommended for most Linux AMIs")
                    elif size_gb > 1000:
                        suggestions.append("Very large volumes may benefit from additional EBS volumes")
                except ValueError:
                    pass

        # RDS-specific suggestions
        elif intent == 'create_rds':
            engine = parameters.get('db_engine', '').lower()
            storage = parameters.get('allocated_storage')

            if engine == 'postgres':
                suggestions.append("PostgreSQL is excellent for complex queries and JSON operations")
            elif engine == 'mysql':
                suggestions.append("MySQL is great for web applications and high concurrency")

            if storage:
                try:
                    storage_gb = int(storage)
                    if storage_gb < 20:
                        suggestions.append("Minimum 20GB recommended for RDS instances")
                except ValueError:
                    pass

        return suggestions

    def get_alternative_suggestions(self, intent: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get alternative options and suggestions for the current request
        """
        alternatives = []

        if intent == 'create_ec2':
            instance_type = parameters.get('ec2_type', '')

            # Suggest alternative instance types
            if 't3.micro' in instance_type:
                alternatives.append({
                    'type': 'instance_alternative',
                    'title': 'Consider T3.small for better performance',
                    'description': 'T3.small offers more CPU credits and better performance for ~$5/month more',
                    'parameters': {'ec2_type': 't3.small'}
                })

            # Suggest cost optimization
            alternatives.append({
                'type': 'cost_optimization',
                'title': 'Use Spot Instances for development',
                'description': 'Save up to 90% with Spot instances for non-production workloads',
                'parameters': {'pricing_model': 'spot'}
            })

        elif intent == 'create_rds':
            engine = parameters.get('db_engine', '').lower()

            if engine == 'postgres':
                alternatives.append({
                    'type': 'engine_alternative',
                    'title': 'Consider Aurora PostgreSQL',
                    'description': 'Aurora offers better performance and automatic scaling',
                    'parameters': {'db_engine': 'aurora-postgresql'}
                })

        return alternatives

    def get_contextual_help(self, current_state: str, intent: str = "") -> List[str]:
        """
        Get contextual help based on current conversation state
        """
        help_suggestions = []

        if current_state == 'collecting_params':
            help_suggestions.extend([
                "You can specify multiple parameters in one message",
                "Use natural language like 'powerful instance' or 'small database'",
                "Type 'help' anytime for more assistance"
            ])

        elif current_state == 'error':
            help_suggestions.extend([
                "Check your AWS credentials and permissions",
                "Verify parameter values are within AWS limits",
                "Try using default values for complex parameters"
            ])

        elif intent.startswith('create_'):
            resource_type = intent.replace('create_', '')
            help_suggestions.append(f"Tell me the specifications for your {resource_type.upper()} or use defaults")

        return help_suggestions

    def get_ai_powered_suggestions(self, message: str, intent: str, context: List[Dict] = None) -> List[str]:
        """
        Get AI-powered suggestions using Perplexity
        """
        context_str = ""
        if context and len(context) > 0:
            recent_messages = context[-3:]
            context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_messages])

        prompt = f"""
        Based on the user's AWS request, provide 2-3 helpful suggestions or recommendations.
        Focus on cost optimization, security best practices, or performance improvements.

        Conversation Context:
        {context_str}

        User Message: {message}
        Detected Intent: {intent}

        Provide suggestions in a natural, conversational way.
        Keep each suggestion concise (under 100 characters).
        Focus on actionable advice.

        Return as a JSON array of strings:
        ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
        """

        try:
            response, error = send_to_perplexity(prompt)
            if error:
                return []

            # Parse JSON response
            try:
                suggestions = eval(response.strip())  # Simple JSON parsing
                if isinstance(suggestions, list):
                    return [str(s) for s in suggestions if s][:3]
            except:
                # Fallback: extract suggestions from text
                lines = response.strip().split('\n')
                suggestions = [line.strip('- "') for line in lines if line.strip()][:3]
                return suggestions

        except Exception as e:
            print(f"AI suggestion error: {e}")

        return []

    def get_completion_suggestions(self, partial_input: str) -> List[str]:
        """
        Get auto-completion suggestions for partial input
        """
        suggestions = []

        partial_lower = partial_input.lower()

        # Common AWS commands
        commands = [
            "create an ec2 instance",
            "create an s3 bucket",
            "create an rds database",
            "list ec2 instances",
            "list s3 buckets",
            "destroy ec2 instance",
            "modify ec2 instance"
        ]

        for cmd in commands:
            if cmd.startswith(partial_lower):
                suggestions.append(cmd)

        # Parameter suggestions
        if "instance type" in partial_lower or "type" in partial_lower:
            suggestions.extend(["t3.micro", "t3.small", "t3.medium", "m5.large"])

        if "region" in partial_lower:
            suggestions.extend(["us-east-1", "us-west-2", "eu-west-1"])

        return suggestions[:5]

# Global instance for easy access
suggestion_engine = SuggestionEngine()

def get_proactive_suggestions(intent: str, parameters: Dict[str, Any], user_id: str = "default_user") -> List[str]:
    """Get proactive suggestions"""
    return suggestion_engine.get_proactive_suggestions(intent, parameters, user_id)

def get_alternative_suggestions(intent: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get alternative suggestions"""
    return suggestion_engine.get_alternative_suggestions(intent, parameters)

def get_contextual_help(current_state: str, intent: str = "") -> List[str]:
    """Get contextual help"""
    return suggestion_engine.get_contextual_help(current_state, intent)

def get_ai_powered_suggestions(message: str, intent: str, context: List[Dict] = None) -> List[str]:
    """Get AI-powered suggestions"""
    return suggestion_engine.get_ai_powered_suggestions(message, intent, context)
