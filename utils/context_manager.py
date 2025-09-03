import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os

@dataclass
class ConversationContext:
    """Represents the current conversation context"""
    user_id: str = "default_user"
    session_id: str = ""
    current_intent: str = ""
    collected_parameters: Dict[str, Any] = None
    conversation_history: List[Dict] = None
    user_preferences: Dict[str, Any] = None
    active_resources: List[Dict] = None
    error_context: Dict[str, Any] = None
    last_activity: datetime = None
    conversation_state: str = "idle"  # idle, collecting_params, executing, error
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.collected_parameters is None:
            self.collected_parameters = {}
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.active_resources is None:
            self.active_resources = []
        if self.error_context is None:
            self.error_context = {}
        if self.last_activity is None:
            self.last_activity = datetime.now()

@dataclass
class UserProfile:
    """Represents user preferences and behavior patterns"""
    user_id: str
    preferred_region: str = "us-east-1"
    common_instance_types: List[str] = None
    default_security_groups: List[str] = None
    cost_budget: float = 0.0
    usage_patterns: Dict[str, Any] = None
    learning_data: Dict[str, Any] = None
    created_at: datetime = None
    last_updated: datetime = None

    def __post_init__(self):
        if self.common_instance_types is None:
            self.common_instance_types = ["t3.micro", "t3.small"]
        if self.default_security_groups is None:
            self.default_security_groups = []
        if self.usage_patterns is None:
            self.usage_patterns = {}
        if self.learning_data is None:
            self.learning_data = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()

class ContextManager:
    """
    Advanced context management system for maintaining conversation state,
    user preferences, and providing context-aware responses.
    """

    def __init__(self, context_file: str = "conversation_context.json",
                 profiles_file: str = "user_profiles.json"):
        self.context_file = context_file
        self.profiles_file = profiles_file
        self.contexts: Dict[str, ConversationContext] = {}
        self.profiles: Dict[str, UserProfile] = {}
        self.max_history_length = 50
        self.session_timeout = timedelta(hours=24)  # 24 hours

        # Load existing data
        self._load_contexts()
        self._load_profiles()

    def _load_contexts(self):
        """Load conversation contexts from file"""
        if os.path.exists(self.context_file):
            try:
                with open(self.context_file, 'r') as f:
                    data = json.load(f)
                    for session_id, context_data in data.items():
                        # Convert string dates back to datetime
                        if 'last_activity' in context_data:
                            context_data['last_activity'] = datetime.fromisoformat(context_data['last_activity'])
                        self.contexts[session_id] = ConversationContext(**context_data)
            except Exception as e:
                print(f"Error loading contexts: {e}")

    def _save_contexts(self):
        """Save conversation contexts to file"""
        try:
            data = {}
            for session_id, context in self.contexts.items():
                context_dict = asdict(context)
                # Convert datetime to string
                if 'last_activity' in context_dict:
                    context_dict['last_activity'] = context.last_activity.isoformat()
                data[session_id] = context_dict

            with open(self.context_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving contexts: {e}")

    def _load_profiles(self):
        """Load user profiles from file"""
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
                    for user_id, profile_data in data.items():
                        # Convert string dates back to datetime
                        for date_field in ['created_at', 'last_updated']:
                            if date_field in profile_data:
                                profile_data[date_field] = datetime.fromisoformat(profile_data[date_field])
                        self.profiles[user_id] = UserProfile(**profile_data)
            except Exception as e:
                print(f"Error loading profiles: {e}")

    def _save_profiles(self):
        """Save user profiles to file"""
        try:
            data = {}
            for user_id, profile in self.profiles.items():
                profile_dict = asdict(profile)
                # Convert datetime to string
                for date_field in ['created_at', 'last_updated']:
                    if date_field in profile_dict:
                        profile_dict[date_field] = profile_dict[date_field].isoformat()
                data[user_id] = profile_dict

            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving profiles: {e}")

    def get_or_create_context(self, session_id: str, user_id: str = "default_user") -> ConversationContext:
        """Get existing context or create new one"""
        # Clean up expired sessions
        self._cleanup_expired_sessions()

        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.last_activity = datetime.now()
            return context

        # Create new context
        context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            last_activity=datetime.now()
        )
        self.contexts[session_id] = context
        self._save_contexts()
        return context

    def update_context(self, session_id: str, **updates):
        """Update conversation context"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            context.last_activity = datetime.now()
            self._save_contexts()

    def add_message_to_history(self, session_id: str, message: Dict):
        """Add message to conversation history"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.conversation_history.append(message)

            # Keep history within limits
            if len(context.conversation_history) > self.max_history_length:
                context.conversation_history = context.conversation_history[-self.max_history_length:]

            context.last_activity = datetime.now()
            self._save_contexts()

    def get_recent_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        if session_id in self.contexts:
            return self.contexts[session_id].conversation_history[-limit:]
        return []

    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile"""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id)
            self._save_profiles()

        return self.profiles[user_id]

    def update_user_profile(self, user_id: str, **updates):
        """Update user profile with new preferences/patterns"""
        profile = self.get_user_profile(user_id)

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.now()
        self._save_profiles()

    def learn_from_interaction(self, session_id: str, intent: str, parameters: Dict):
        """Learn from user interactions to improve future suggestions"""
        if session_id not in self.contexts:
            return

        context = self.contexts[session_id]
        user_id = context.user_id
        profile = self.get_user_profile(user_id)

        # Update usage patterns
        if intent not in profile.usage_patterns:
            profile.usage_patterns[intent] = {'count': 0, 'parameters': {}}

        profile.usage_patterns[intent]['count'] += 1

        # Learn parameter preferences
        for param, value in parameters.items():
            if param not in profile.usage_patterns[intent]['parameters']:
                profile.usage_patterns[intent]['parameters'][param] = {}

            param_patterns = profile.usage_patterns[intent]['parameters'][param]
            if value not in param_patterns:
                param_patterns[value] = 0
            param_patterns[value] += 1

        # Update common instance types
        if 'ec2_type' in parameters:
            instance_type = parameters['ec2_type']
            if instance_type not in profile.common_instance_types:
                profile.common_instance_types.append(instance_type)
                # Keep only top 5 most common
                if len(profile.common_instance_types) > 5:
                    profile.common_instance_types = profile.common_instance_types[-5:]

        profile.last_updated = datetime.now()
        self._save_profiles()

    def get_smart_defaults(self, user_id: str, intent: str) -> Dict[str, Any]:
        """Get intelligent defaults based on user history"""
        profile = self.get_user_profile(user_id)
        defaults = {}

        # Set preferred region only for resources that need it explicitly
        # EC2 uses availability zone which includes region info, so skip region for EC2
        # S3, RDS, DynamoDB, and IAM are global resources and don't need explicit region parameter
        if intent not in ['create_ec2', 'create_s3', 'create_rds', 'create_dynamodb', 'create_iam_user', 'create_iam_role', 'create_iam_policy']:
            defaults['region'] = profile.preferred_region

        # Set common instance type for EC2
        if intent == 'create_ec2' and profile.common_instance_types:
            defaults['ec2_type'] = profile.common_instance_types[-1]  # Most recent

        return defaults

    def get_contextual_suggestions(self, session_id: str) -> List[str]:
        """Get contextual suggestions based on current conversation state"""
        if session_id not in self.contexts:
            return []

        context = self.contexts[session_id]
        suggestions = []

        # Suggestions based on current intent
        if context.current_intent.startswith('create_'):
            resource_type = context.current_intent.replace('create_', '')
            suggestions.append(f"Would you like to add security groups to your {resource_type}?")
            suggestions.append(f"Consider setting up monitoring for your {resource_type}.")

        elif context.current_intent.startswith('destroy_'):
            suggestions.append("Are you sure you want to destroy this resource?")
            suggestions.append("Have you backed up any important data?")

        # Suggestions based on user history
        profile = self.get_user_profile(context.user_id)
        if profile.usage_patterns:
            most_common_intent = max(profile.usage_patterns.items(),
                                   key=lambda x: x[1]['count'])[0]
            suggestions.append(f"Based on your history, you often {most_common_intent.replace('_', ' ')}.")

        return suggestions[:3]  # Return up to 3 suggestions

    def detect_conversation_patterns(self, session_id: str) -> Dict[str, Any]:
        """Detect patterns in user conversation behavior"""
        if session_id not in self.contexts:
            return {}

        context = self.contexts[session_id]
        history = context.conversation_history

        patterns = {
            'frequent_intents': {},
            'error_frequency': 0,
            'avg_response_time': 0,
            'preferred_times': []
        }

        # Analyze intent frequency
        for message in history:
            if message.get('role') == 'user':
                content = message.get('content', '').lower()
                # Simple pattern detection (could be enhanced with NLP)
                if 'create' in content:
                    patterns['frequent_intents']['create'] = patterns['frequent_intents'].get('create', 0) + 1
                elif 'destroy' in content:
                    patterns['frequent_intents']['destroy'] = patterns['frequent_intents'].get('destroy', 0) + 1
                elif 'list' in content:
                    patterns['frequent_intents']['list'] = patterns['frequent_intents'].get('list', 0) + 1

        return patterns

    def _cleanup_expired_sessions(self):
        """Remove expired conversation sessions"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, context in self.contexts.items():
            if current_time - context.last_activity > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.contexts[session_id]

        if expired_sessions:
            self._save_contexts()

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the current conversation"""
        if session_id not in self.contexts:
            return {}

        context = self.contexts[session_id]
        return {
            'session_id': session_id,
            'current_intent': context.current_intent,
            'state': context.conversation_state,
            'parameters_collected': len(context.collected_parameters),
            'messages_count': len(context.conversation_history),
            'active_resources': len(context.active_resources),
            'last_activity': context.last_activity.isoformat(),
            'confidence': context.confidence_score
        }

# Global instance for easy access
context_manager = ContextManager()

def get_context(session_id: str, user_id: str = "default_user") -> ConversationContext:
    """Get conversation context"""
    return context_manager.get_or_create_context(session_id, user_id)

def update_context(session_id: str, **updates):
    """Update conversation context"""
    context_manager.update_context(session_id, **updates)

def add_message_to_history(session_id: str, message: Dict):
    """Add message to conversation history"""
    context_manager.add_message_to_history(session_id, message)

def get_recent_history(session_id: str, limit: int = 10) -> List[Dict]:
    """Get recent conversation history"""
    return context_manager.get_recent_history(session_id, limit)

def get_user_profile(user_id: str) -> UserProfile:
    """Get user profile"""
    return context_manager.get_user_profile(user_id)

def learn_from_interaction(session_id: str, intent: str, parameters: Dict):
    """Learn from user interaction"""
    context_manager.learn_from_interaction(session_id, intent, parameters)

def get_smart_defaults(user_id: str, intent: str) -> Dict[str, Any]:
    """Get smart defaults for user"""
    return context_manager.get_smart_defaults(user_id, intent)

def get_contextual_suggestions(session_id: str) -> List[str]:
    """Get contextual suggestions"""
    return context_manager.get_contextual_suggestions(session_id)
