"""
Command Parser for SURFACE layer.

Parses natural language commands and extracts structured intent using lightweight models.
Implements caching for common command patterns.
"""
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from insanity_cluster.common.models import ParsedCommand
from insanity_cluster.common.config import settings
from insanity_cluster.table.redis_manager import RedisManager

logger = logging.getLogger(__name__)


@dataclass
class Ambiguity:
    """Represents an ambiguous command that needs clarification"""
    command: str
    possible_intents: List[str]
    missing_parameters: List[str]
    confidence: float
    reason: str


@dataclass
class ClarificationPrompt:
    """Clarification questions to resolve ambiguity"""
    questions: List[str]
    suggested_intents: List[str]
    context: Dict[str, Any]


class ParseError(Exception):
    """Raised when command parsing fails"""
    pass


class CommandParser:
    """
    Parse natural language commands into structured format.
    
    Uses lightweight models (gpt-5-nano) for fast parsing with Redis caching
    for common command patterns.
    """
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        """
        Initialize command parser.
        
        Args:
            redis_manager: Redis manager for caching (optional)
        """
        self.redis_manager = redis_manager
        self.cache_ttl = settings.command_cache_ttl_days * 24 * 3600  # Convert to seconds
        self.confidence_threshold = 0.8
        
        # Common intent patterns for quick matching
        self.intent_patterns = {
            "code_generation": ["write", "create", "generate", "build", "implement", "code"],
            "code_review": ["review", "analyze", "check", "audit", "inspect"],
            "llc_formation": ["form", "create", "establish", "register", "llc", "company"],
            "contract_review": ["review contract", "analyze contract", "check contract"],
            "email": ["send email", "compose email", "write email", "email"],
            "phone_call": ["call", "phone", "dial", "ring"],
            "research": ["research", "find", "search", "investigate", "gather"],
            "schedule": ["schedule", "book", "arrange", "set up meeting"],
            "financial": ["calculate", "budget", "invoice", "accounting", "financial"],
        }
        
        logger.info("CommandParser initialized")
    
    def parse(self, raw_command: str, user_id: str) -> ParsedCommand:
        """
        Parse natural language command into structured format.
        
        Args:
            raw_command: Raw natural language command from user
            user_id: User ID for context
            
        Returns:
            ParsedCommand with intent, parameters, and confidence score
            
        Raises:
            ParseError: If command is ambiguous or cannot be parsed
        """
        logger.info(f"Parsing command for user {user_id}: {raw_command[:100]}")
        
        # Check cache first
        cached_result = self._get_cached_parse(raw_command)
        if cached_result:
            logger.info("Using cached parse result")
            cached_result.user_id = user_id
            return cached_result
        
        # Quick pattern matching for common intents
        intent, confidence = self._quick_intent_match(raw_command)
        
        if confidence >= self.confidence_threshold:
            # High confidence - extract parameters directly
            parameters = self._extract_parameters(raw_command, intent)
            parsed = ParsedCommand(
                intent=intent,
                parameters=parameters,
                confidence=confidence,
                user_id=user_id,
                timestamp=self._get_timestamp()
            )
            
            # Cache the result
            self._cache_parse(raw_command, parsed)
            
            logger.info(f"Parsed command with intent: {intent}, confidence: {confidence}")
            return parsed
        
        # Low confidence - need model-based parsing
        parsed = self._model_based_parse(raw_command, user_id)
        
        if parsed.confidence < self.confidence_threshold:
            # Still low confidence - request clarification
            ambiguity = Ambiguity(
                command=raw_command,
                possible_intents=[parsed.intent],
                missing_parameters=self._identify_missing_params(parsed),
                confidence=parsed.confidence,
                reason="Low confidence in intent detection"
            )
            raise ParseError(f"Ambiguous command: {self.request_clarification(ambiguity)}")
        
        # Cache successful parse
        self._cache_parse(raw_command, parsed)
        
        logger.info(f"Model-parsed command with intent: {parsed.intent}, confidence: {parsed.confidence}")
        return parsed
    
    def request_clarification(self, ambiguity: Ambiguity) -> ClarificationPrompt:
        """
        Generate specific questions to resolve ambiguity.
        
        Args:
            ambiguity: Ambiguity information
            
        Returns:
            ClarificationPrompt with questions and suggestions
        """
        questions = []
        
        # Generate questions based on ambiguity type
        if len(ambiguity.possible_intents) > 1:
            intents_str = ", ".join(ambiguity.possible_intents)
            questions.append(
                f"I'm not sure what you want to do. Did you mean: {intents_str}?"
            )
        
        if ambiguity.missing_parameters:
            for param in ambiguity.missing_parameters:
                questions.append(f"What {param} should I use?")
        
        if not questions:
            questions.append(
                "Could you please rephrase your request with more details?"
            )
        
        return ClarificationPrompt(
            questions=questions,
            suggested_intents=ambiguity.possible_intents,
            context={"original_command": ambiguity.command}
        )
    
    def _quick_intent_match(self, command: str) -> tuple[str, float]:
        """
        Quick pattern matching for common intents.
        
        Args:
            command: Raw command text
            
        Returns:
            Tuple of (intent, confidence)
        """
        command_lower = command.lower()
        
        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in command_lower:
                    # Calculate confidence based on keyword match
                    confidence = 0.9 if len(keyword.split()) > 1 else 0.85
                    return intent, confidence
        
        return "general_task", 0.5
    
    def _extract_parameters(self, command: str, intent: str) -> Dict[str, Any]:
        """
        Extract parameters from command based on intent.
        
        Args:
            command: Raw command text
            intent: Detected intent
            
        Returns:
            Dictionary of extracted parameters
        """
        parameters = {
            "raw_command": command,
            "intent_type": intent
        }
        
        # Intent-specific parameter extraction
        if intent == "code_generation":
            parameters["language"] = self._extract_language(command)
            parameters["description"] = command
        
        elif intent == "email":
            parameters["recipient"] = self._extract_email_recipient(command)
            parameters["subject"] = self._extract_email_subject(command)
            parameters["body"] = command
        
        elif intent == "llc_formation":
            parameters["state"] = self._extract_state(command)
            parameters["company_name"] = self._extract_company_name(command)
        
        return parameters
    
    def _model_based_parse(self, command: str, user_id: str) -> ParsedCommand:
        """
        Use lightweight model for parsing when pattern matching fails.
        
        Integrates with PAN layer using gpt-5-nano for fast, cost-effective parsing.
        
        Args:
            command: Raw command text
            user_id: User ID
            
        Returns:
            ParsedCommand
        """
        # For now, use pattern matching with lower confidence
        # Full PAN layer integration would be added here when model_router is available
        # This allows the system to work without requiring model_router dependency
        intent, confidence = self._quick_intent_match(command)
        parameters = self._extract_parameters(command, intent)
        
        from datetime import datetime
        return ParsedCommand(
            intent=intent,
            parameters=parameters,
            confidence=confidence * 0.9,  # Reduce confidence slightly
            user_id=user_id,
            timestamp=datetime.utcnow()
        )
    
    def _get_cached_parse(self, command: str) -> Optional[ParsedCommand]:
        """Get cached parse result from Redis"""
        if not self.redis_manager:
            return None
        
        cache_key = self._get_cache_key(command)
        try:
            cached_data = self.redis_manager.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                from datetime import datetime
                return ParsedCommand(
                    intent=data["intent"],
                    parameters=data["parameters"],
                    confidence=data["confidence"],
                    user_id="",  # Will be set by caller
                    timestamp=datetime.fromisoformat(data["timestamp"])
                )
        except Exception as e:
            logger.warning(f"Failed to get cached parse: {e}")
        
        return None
    
    def _cache_parse(self, command: str, parsed: ParsedCommand) -> None:
        """Cache parse result in Redis"""
        if not self.redis_manager:
            return
        
        cache_key = self._get_cache_key(command)
        try:
            data = {
                "intent": parsed.intent,
                "parameters": parsed.parameters,
                "confidence": parsed.confidence,
                "timestamp": parsed.timestamp.isoformat()
            }
            self.redis_manager.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Failed to cache parse: {e}")
    
    def _get_cache_key(self, command: str) -> str:
        """Generate cache key for command"""
        command_hash = hashlib.sha256(command.encode()).hexdigest()
        return f"command_parse:{command_hash}"
    
    def _identify_missing_params(self, parsed: ParsedCommand) -> List[str]:
        """Identify missing required parameters"""
        missing = []
        
        if parsed.intent == "email":
            if "recipient" not in parsed.parameters or not parsed.parameters["recipient"]:
                missing.append("recipient email address")
            if "subject" not in parsed.parameters or not parsed.parameters["subject"]:
                missing.append("email subject")
        
        elif parsed.intent == "llc_formation":
            if "state" not in parsed.parameters or not parsed.parameters["state"]:
                missing.append("state for LLC formation")
            if "company_name" not in parsed.parameters or not parsed.parameters["company_name"]:
                missing.append("company name")
        
        return missing
    
    def _extract_language(self, command: str) -> Optional[str]:
        """Extract programming language from command"""
        languages = ["python", "javascript", "java", "c++", "go", "rust", "typescript"]
        command_lower = command.lower()
        
        for lang in languages:
            if lang in command_lower:
                return lang
        
        return None
    
    def _extract_email_recipient(self, command: str) -> Optional[str]:
        """Extract email recipient from command"""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, command)
        return matches[0] if matches else None
    
    def _extract_email_subject(self, command: str) -> Optional[str]:
        """Extract email subject from command"""
        # Look for patterns like "subject: ..." or "about ..."
        import re
        subject_patterns = [
            r'subject[:\s]+([^,\.]+)',
            r'about\s+([^,\.]+)',
            r'regarding\s+([^,\.]+)'
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_state(self, command: str) -> Optional[str]:
        """Extract US state from command"""
        states = [
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
            "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
            "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
            "maine", "maryland", "massachusetts", "michigan", "minnesota",
            "mississippi", "missouri", "montana", "nebraska", "nevada",
            "new hampshire", "new jersey", "new mexico", "new york",
            "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
            "pennsylvania", "rhode island", "south carolina", "south dakota",
            "tennessee", "texas", "utah", "vermont", "virginia", "washington",
            "west virginia", "wisconsin", "wyoming"
        ]
        
        command_lower = command.lower()
        for state in states:
            if state in command_lower:
                return state.title()
        
        return None
    
    def _extract_company_name(self, command: str) -> Optional[str]:
        """Extract company name from command"""
        import re
        # Look for patterns like "called ...", "named ...", or quoted text
        patterns = [
            r'called\s+"([^"]+)"',
            r'named\s+"([^"]+)"',
            r'"([^"]+)"\s+llc',
            r'llc\s+called\s+([^,\.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow()
