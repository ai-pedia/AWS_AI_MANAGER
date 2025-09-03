import re
import json
from typing import Dict, List, Tuple, Optional
from utils.ai_client import send_to_perplexity

class IntentClassifier:
    """
    Enhanced intent classification system that combines regex patterns with AI-powered analysis
    for more accurate and context-aware intent recognition.
    """

    def __init__(self):
        # Define intent patterns with priorities
        self.intent_patterns = {
            'create_ec2': [
                r'\b(create|build|launch|provision)\s+(an?\s+)?(ec2|instance)\b',
                r'\b(make|setup|deploy)\s+(an?\s+)?ec2\b',
                r'\bspin\s+up\s+(an?\s+)?ec2\b'
            ],
            'create_s3': [
                r'\b(create|make|build)\s+(an?\s+)?s3(\s+bucket)?\b',
                r'\b(set\s+up|provision)\s+(an?\s+)?s3\b'
            ],
            'create_rds': [
                r'\b(create|make|build|provision)\s+(an?\s+)?rds(\s+instance)?\b',
                r'\b(set\s+up|deploy)\s+(an?\s+)?rds\b'
            ],
            'create_dynamodb': [
                r'\b(create|make|build)\s+(a\s+)?dynamodb(\s+table)?\b',
                r'\b(set\s+up|provision)\s+(a\s+)?dynamodb\b'
            ],
            'create_iam_user': [
                r'\b(create|make|add)\s+(an?\s+)?iam\s+user\b'
            ],
            'create_iam_role': [
                r'\b(create|make|add)\s+(an?\s+)?iam\s+role\b'
            ],
            'create_iam_policy': [
                r'\b(create|make|add)\s+(an?\s+)?iam\s+policy\b'
            ],
            'destroy_ec2': [
                r'\b(destroy|delete|terminate|remove)\s+(an?\s+)?(ec2|instance)\b'
            ],
            'destroy_s3': [
                r'\b(destroy|delete|remove)\s+(an?\s+)?s3(\s+bucket)?\b'
            ],
            'destroy_rds': [
                r'\b(destroy|delete|terminate|remove)\s+(an?\s+)?rds(\s+instance)?\b'
            ],
            'destroy_dynamodb': [
                r'\b(destroy|delete|remove)\s+(a\s+)?dynamodb(\s+table)?\b'
            ],
            'destroy_iam_user': [
                r'\b(destroy|delete|remove)\s+(an?\s+)?iam\s+user\b'
            ],
            'destroy_iam_role': [
                r'\b(destroy|delete|remove)\s+(an?\s+)?iam\s+role\b'
            ],
            'destroy_iam_policy': [
                r'\b(destroy|delete|remove)\s+(an?\s+)?iam\s+policy\b'
            ],
            'list_ec2': [
                r'\b(list|show|display)\s+(all\s+)?(ec2|instance)s?\b'
            ],
            'list_s3': [
                r'\b(list|show|display)\s+(all\s+)?s3(\s+buckets?)?\b'
            ],
            'list_rds': [
                r'\b(list|show|display)\s+(all\s+)?rds(\s+instances?)?\b'
            ],
            'list_dynamodb': [
                r'\b(list|show|display)\s+(all\s+)?dynamodb(\s+tables?)?\b'
            ],
            'list_iam_user': [
                r'\b(list|show|display)\s+(all\s+)?iam\s+users?\b'
            ],
            'list_iam_role': [
                r'\b(list|show|display)\s+(all\s+)?iam\s+roles?\b'
            ],
            'list_iam_policy': [
                r'\b(list|show|display)\s+(all\s+)?iam\s+policies?\b'
            ],
            'modify_ec2': [
                r'\b(modify|change|update|edit)\s+(an?\s+)?(ec2|instance)\b'
            ],
            'cost_estimation': [
                r'\b(cost|estimate|pricing)\s+(of|for)\b',
                r'\bhow\s+much\s+(does|will)\b'
            ],
            'help': [
                r'\b(help|assist|support)\b',
                r'\bwhat\s+can\s+you\s+do\b'
            ],
            'status': [
                r'\b(status|health|check)\b'
            ]
        }

        # Compound intent patterns
        self.compound_patterns = {
            'create_multiple': [
                r'\b(create|build|launch)\s+(multiple|several|many)\b',
                r'\b(set\s+up|provision)\s+(multiple|several)\b'
            ]
        }

    def classify_intent_regex(self, message: str) -> Tuple[Optional[str], float]:
        """
        Classify intent using regex patterns
        Returns: (intent_name, confidence_score)
        """
        message_lower = message.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent, 0.8  # High confidence for regex matches

        return None, 0.0

    def classify_intent_ai(self, message: str, context: List[Dict] = None) -> Tuple[Optional[str], float, Dict]:
        """
        Classify intent using AI analysis
        Returns: (intent_name, confidence_score, extracted_parameters)
        """
        context_str = ""
        if context and len(context) > 0:
            recent_messages = context[-3:]  # Last 3 messages for context
            context_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_messages])

        prompt = f"""
        Analyze the user's message and classify their intent for AWS resource management.
        Consider the conversation context if provided.

        Conversation Context:
        {context_str}

        Current Message: {message}

        Available Intents:
        - create_ec2: Create EC2 instance
        - create_s3: Create S3 bucket
        - create_rds: Create RDS instance
        - create_dynamodb: Create DynamoDB table
        - create_iam_user: Create IAM user
        - create_iam_role: Create IAM role
        - create_iam_policy: Create IAM policy
        - destroy_ec2: Destroy EC2 instance
        - destroy_s3: Destroy S3 bucket
        - destroy_rds: Destroy RDS instance
        - destroy_dynamodb: Destroy DynamoDB table
        - destroy_iam_user: Destroy IAM user
        - destroy_iam_role: Destroy IAM role
        - destroy_iam_policy: Destroy IAM policy
        - list_ec2: List EC2 instances
        - list_s3: List S3 buckets
        - list_rds: List RDS instances
        - list_dynamodb: List DynamoDB tables
        - list_iam_user: List IAM users
        - list_iam_role: List IAM roles
        - list_iam_policy: List IAM policies
        - modify_ec2: Modify EC2 instance
        - cost_estimation: Estimate costs
        - help: Request help
        - status: Check status

        Also extract any parameters mentioned in the message.

        Return your response in this exact JSON format:
        {{
            "intent": "intent_name",
            "confidence": 0.95,
            "parameters": {{
                "instance_type": "t3.micro",
                "region": "us-east-1",
                "bucket_name": "my-bucket"
            }},
            "reasoning": "Brief explanation of why this intent was chosen"
        }}

        If no clear intent is found, return:
        {{
            "intent": "unknown",
            "confidence": 0.0,
            "parameters": {{}},
            "reasoning": "No clear AWS-related intent detected"
        }}
        """

        try:
            response, error = send_to_perplexity(prompt)
            if error:
                return None, 0.0, {}

            # Parse JSON response
            try:
                result = json.loads(response.strip())
                intent = result.get('intent', 'unknown')
                confidence = result.get('confidence', 0.0)
                parameters = result.get('parameters', {})

                return intent, confidence, parameters
            except json.JSONDecodeError:
                # Fallback: try to extract intent from text response
                return self._extract_intent_from_text(response), 0.5, {}

        except Exception as e:
            print(f"AI classification error: {e}")
            return None, 0.0, {}

    def _extract_intent_from_text(self, response: str) -> Optional[str]:
        """Extract intent from text response as fallback"""
        response_lower = response.lower()

        for intent in self.intent_patterns.keys():
            if intent.replace('_', ' ') in response_lower:
                return intent

        return None

    def classify_intent_hybrid(self, message: str, context: List[Dict] = None) -> Tuple[str, float, Dict]:
        """
        Hybrid classification combining regex and AI approaches
        Returns: (intent_name, confidence_score, extracted_parameters)
        """
        # First try regex classification (fast and reliable)
        regex_intent, regex_confidence = self.classify_intent_regex(message)

        # If regex confidence is high enough, use it
        if regex_confidence >= 0.8:
            return regex_intent, regex_confidence, {}

        # Otherwise, use AI classification
        ai_intent, ai_confidence, ai_parameters = self.classify_intent_ai(message, context)

        # If AI confidence is higher, use AI result
        if ai_confidence > regex_confidence:
            return ai_intent, ai_confidence, ai_parameters

        # If regex found something but AI didn't, use regex
        if regex_intent and (not ai_intent or ai_intent == 'unknown'):
            return regex_intent, regex_confidence, {}

        # If AI found something better, use AI
        if ai_intent and ai_intent != 'unknown':
            return ai_intent, ai_confidence, ai_parameters

        # Default fallback
        return 'unknown', 0.0, {}

    def get_intent_suggestions(self, message: str) -> List[str]:
        """
        Provide intent suggestions when classification is uncertain
        """
        suggestions = []
        message_lower = message.lower()

        # Check for partial matches
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                # Remove word boundaries and make more flexible
                flexible_pattern = pattern.replace(r'\b', '').replace(r'\s+', r'\s*')
                if re.search(flexible_pattern, message_lower, re.IGNORECASE):
                    suggestions.append(intent)
                    break

        return list(set(suggestions))[:3]  # Return up to 3 unique suggestions

    def validate_intent_context(self, intent: str, context: List[Dict]) -> bool:
        """
        Validate if the intent makes sense given the conversation context
        """
        if not context:
            return True

        # Check for contradictory intents in recent context
        recent_intents = []
        for msg in context[-5:]:  # Check last 5 messages
            if msg.get('role') == 'assistant' and 'intent' in msg.get('content', '').lower():
                # Extract intent from assistant responses
                content = msg.get('content', '').lower()
                for intent_name in self.intent_patterns.keys():
                    if intent_name.replace('_', ' ') in content:
                        recent_intents.append(intent_name)

        # Check for logical contradictions
        if intent.startswith('create_') and any(i.startswith('destroy_') for i in recent_intents):
            return False  # Creating right after destroying might be confusing

        if intent.startswith('destroy_') and any(i.startswith('create_') for i in recent_intents):
            return False  # Destroying right after creating might be a mistake

        return True

# Global instance for easy access
intent_classifier = IntentClassifier()

def classify_intent(message: str, context: List[Dict] = None) -> Tuple[str, float, Dict]:
    """
    Main function to classify intent using hybrid approach
    """
    return intent_classifier.classify_intent_hybrid(message, context)

def get_intent_suggestions(message: str) -> List[str]:
    """
    Get intent suggestions for uncertain cases
    """
    return intent_classifier.get_intent_suggestions(message)

def validate_intent_context(intent: str, context: List[Dict]) -> bool:
    """
    Validate intent against conversation context
    """
    return intent_classifier.validate_intent_context(intent, context)
