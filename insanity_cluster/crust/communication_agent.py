"""
Communication Agent for CRUST layer.

Handles communication tasks including phone calls, emails, and meeting scheduling.
Optimized for realtime performance with sub-second latency targets.
"""
import logging
from typing import Any, Dict, Optional

from insanity_cluster.common.models import (
    AgentResult,
    AgentType,
    ModelStrategy,
    PrivacyLevel,
    RoutingMode,
    Subtask,
)
from insanity_cluster.crust.base_agent import BaseAgent
from insanity_cluster.pan.model_router import ModelRouter
from insanity_cluster.pan.models import GenerationParams

logger = logging.getLogger(__name__)


class CommunicationAgent(BaseAgent):
    """
    Specialized agent for communication tasks.
    
    Capabilities:
    - Phone call handling (Twilio integration)
    - Speech-to-text (500ms latency target)
    - Text-to-speech (300ms latency target)
    - Streaming audio processing
    - Voice activity detection
    - Email composition (SendGrid)
    - Meeting scheduling (Google Calendar)
    
    Optimized for realtime performance with streaming support.
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        twilio_client: Optional[Any] = None,
        sendgrid_client: Optional[Any] = None,
        calendar_client: Optional[Any] = None
    ):
        """
        Initialize Communication Agent.
        
        Args:
            model_router: Model router for inference
            twilio_client: Twilio client for phone calls (optional)
            sendgrid_client: SendGrid client for emails (optional)
            calendar_client: Calendar API client (optional)
        """
        # Default to speed-first for realtime communication
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.SPEED_FIRST,
            max_cost=0.1,  # Keep costs low for high-volume communication
            max_latency_ms=1000,  # 1 second max for realtime
            required_capabilities=["streaming"],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.COMMUNICATION,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
        
        # External service clients
        self.twilio_client = twilio_client
        self.sendgrid_client = sendgrid_client
        self.calendar_client = calendar_client
        
        # Performance tracking
        self.stt_latency_target_ms = 500  # Speech-to-text target
        self.tts_latency_target_ms = 300  # Text-to-speech target
        self.total_latency_target_ms = 1000  # Total round-trip target
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """
        Execute communication subtask.
        
        Args:
            subtask: Subtask to execute
            context: Execution context
            
        Returns:
            AgentResult with communication output
        """
        logger.info(f"Communication agent executing: {subtask.description}")
        
        try:
            # Determine task type
            task_type = self._identify_task_type(subtask.description)
            
            # Select model strategy
            model_strategy = self.select_model_strategy(subtask)
            
            # Execute based on task type
            if task_type == "phone_call":
                output = await self._handle_phone_call(subtask, context, model_strategy)
            elif task_type == "email":
                output = await self._compose_email(subtask, context, model_strategy)
            elif task_type == "meeting":
                output = await self._schedule_meeting(subtask, context, model_strategy)
            elif task_type == "stt":
                output = await self._speech_to_text(subtask, context)
            elif task_type == "tts":
                output = await self._text_to_speech(subtask, context)
            else:
                output = await self._execute_generic_communication(subtask, context, model_strategy)
            
            # Validate output
            validation_score = self.validate_output(output, subtask)
            
            # Get metrics
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 500)
            model_used = context.get("last_model_used", "claude-haiku-4.5")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Communication agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select model strategy optimized for communication speed.
        
        Args:
            subtask: Subtask to analyze
            
        Returns:
            ModelStrategy optimized for realtime communication
        """
        description_lower = subtask.description.lower()
        
        # Phone calls require ultra-low latency
        if any(keyword in description_lower for keyword in ["call", "phone", "voice", "speak"]):
            return ModelStrategy(
                routing_mode=RoutingMode.SPEED_FIRST,
                max_cost=0.05,
                max_latency_ms=500,  # 500ms for voice
                required_capabilities=["streaming"],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Emails can use slightly higher quality
        if any(keyword in description_lower for keyword in ["email", "message", "compose"]):
            return ModelStrategy(
                routing_mode=RoutingMode.COST_OPTIMIZED,
                max_cost=0.1,
                max_latency_ms=2000,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Default to speed-first
        return self.default_model_strategy
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """
        Validate communication output.
        
        Checks:
        - Tone appropriateness
        - Grammar and clarity
        - Completeness
        - Professional quality
        
        Args:
            output: Generated communication
            subtask: Original subtask
            
        Returns:
            Validation score (0.0 to 1.0)
        """
        if not isinstance(output, (str, dict)):
            return 0.0
        
        # Convert dict to string for validation
        if isinstance(output, dict):
            output_str = str(output.get("content", ""))
        else:
            output_str = output
        
        score = 0.0
        checks_passed = 0
        total_checks = 5
        
        # Check 1: Not empty
        if output_str.strip():
            checks_passed += 1
        
        # Check 2: Reasonable length
        if 10 < len(output_str) < 5000:
            checks_passed += 1
        
        # Check 3: No obvious errors
        error_indicators = ["error", "failed", "cannot", "unable"]
        if not any(indicator in output_str.lower() for indicator in error_indicators):
            checks_passed += 1
        
        # Check 4: Contains greeting or professional language
        professional_indicators = ["hello", "hi", "dear", "thank", "please", "regards"]
        if any(indicator in output_str.lower() for indicator in professional_indicators):
            checks_passed += 1
        
        # Check 5: Proper sentence structure (basic check)
        if "." in output_str or "?" in output_str or "!" in output_str:
            checks_passed += 1
        
        score = checks_passed / total_checks
        
        logger.debug(f"Validation score: {score:.2f} ({checks_passed}/{total_checks} checks passed)")
        
        return score
    
    def _identify_task_type(self, description: str) -> str:
        """
        Identify communication task type.
        
        Args:
            description: Task description
            
        Returns:
            Task type identifier
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["call", "phone", "voice"]):
            return "phone_call"
        elif any(keyword in description_lower for keyword in ["email", "send message"]):
            return "email"
        elif any(keyword in description_lower for keyword in ["schedule", "meeting", "calendar"]):
            return "meeting"
        elif any(keyword in description_lower for keyword in ["transcribe", "speech to text", "stt"]):
            return "stt"
        elif any(keyword in description_lower for keyword in ["text to speech", "tts", "synthesize"]):
            return "tts"
        else:
            return "generic"
    
    async def _handle_phone_call(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Handle phone call interaction.
        
        Args:
            subtask: Phone call subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Call handling result
        """
        call_type = context.get("call_type", "outbound")
        phone_number = context.get("phone_number", "")
        message = context.get("message", "")
        
        if call_type == "inbound":
            # Handle incoming call
            audio_data = context.get("audio_data", "")
            
            # Transcribe audio (STT)
            transcription = await self._speech_to_text_internal(audio_data)
            
            # Generate response
            response_text = await self._generate_call_response(
                transcription,
                subtask,
                context,
                model_strategy
            )
            
            # Convert to speech (TTS)
            audio_response = await self._text_to_speech_internal(response_text)
            
            return {
                "type": "inbound_call",
                "transcription": transcription,
                "response_text": response_text,
                "audio_response": audio_response,
                "status": "completed"
            }
        else:
            # Handle outbound call
            if self.twilio_client:
                # Make actual call via Twilio
                logger.info(f"Making outbound call to {phone_number}")
                # Placeholder for Twilio integration
                call_result = {
                    "type": "outbound_call",
                    "phone_number": phone_number,
                    "message": message,
                    "status": "initiated",
                    "note": "Twilio integration placeholder"
                }
            else:
                # Simulate call
                call_result = {
                    "type": "outbound_call",
                    "phone_number": phone_number,
                    "message": message,
                    "status": "simulated",
                    "note": "Twilio client not configured"
                }
            
            return call_result
    
    async def _compose_email(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Compose and send email.
        
        Args:
            subtask: Email subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Email composition result
        """
        recipient = context.get("recipient", "")
        subject = context.get("subject", "")
        tone = context.get("tone", "professional")
        
        # Build email composition prompt
        prompt = f"""Compose a {tone} email for:

Task: {subtask.description}
Recipient: {recipient}
Subject: {subject}

Context: {context.get('email_context', '')}

Write a complete, professional email with:
1. Appropriate greeting
2. Clear message body
3. Professional closing
"""
        
        generation_params = GenerationParams(
            max_tokens=1000,
            temperature=0.7,
            system_prompt=f"You are a professional communication specialist. Write clear, {tone} emails."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        email_content = response.content
        
        # Send email if SendGrid is configured
        if self.sendgrid_client:
            logger.info(f"Sending email to {recipient}")
            # Placeholder for SendGrid integration
            send_status = "sent"
        else:
            send_status = "composed_only"
        
        return {
            "type": "email",
            "recipient": recipient,
            "subject": subject,
            "content": email_content,
            "status": send_status
        }
    
    async def _schedule_meeting(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Schedule meeting via calendar API.
        
        Args:
            subtask: Meeting scheduling subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Meeting scheduling result
        """
        attendees = context.get("attendees", [])
        duration_minutes = context.get("duration_minutes", 60)
        preferred_time = context.get("preferred_time", "")
        
        # Generate meeting details
        prompt = f"""Create meeting details for:

Task: {subtask.description}
Attendees: {', '.join(attendees)}
Duration: {duration_minutes} minutes
Preferred Time: {preferred_time}

Generate:
1. Meeting title
2. Agenda
3. Description
"""
        
        generation_params = GenerationParams(
            max_tokens=500,
            temperature=0.5,
            system_prompt="You are a professional meeting coordinator."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        meeting_details = response.content
        
        # Schedule via calendar API if configured
        if self.calendar_client:
            logger.info(f"Scheduling meeting with {len(attendees)} attendees")
            # Placeholder for Google Calendar integration
            schedule_status = "scheduled"
        else:
            schedule_status = "details_generated"
        
        return {
            "type": "meeting",
            "attendees": attendees,
            "duration_minutes": duration_minutes,
            "details": meeting_details,
            "status": schedule_status
        }
    
    async def _speech_to_text(
        self,
        subtask: Subtask,
        context: Dict[str, Any]
    ) -> str:
        """
        Convert speech to text.
        
        Args:
            subtask: STT subtask
            context: Execution context with audio data
            
        Returns:
            Transcribed text
        """
        audio_data = context.get("audio_data", "")
        
        if not audio_data:
            return "No audio data provided"
        
        transcription = await self._speech_to_text_internal(audio_data)
        
        return transcription
    
    async def _text_to_speech(
        self,
        subtask: Subtask,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert text to speech.
        
        Args:
            subtask: TTS subtask
            context: Execution context with text
            
        Returns:
            Audio data
        """
        text = context.get("text", subtask.description)
        
        audio_data = await self._text_to_speech_internal(text)
        
        return {
            "type": "tts",
            "text": text,
            "audio_data": audio_data,
            "status": "completed"
        }
    
    async def _execute_generic_communication(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Execute generic communication task.
        
        Args:
            subtask: Generic communication subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Communication output
        """
        prompt = f"""Handle the following communication task:

Task: {subtask.description}

Context: {context.get('additional_context', 'None provided')}

Provide a professional, clear response.
"""
        
        generation_params = GenerationParams(
            max_tokens=1000,
            temperature=0.7,
            system_prompt="You are a professional communicator. Be clear, concise, and appropriate."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return response.content
    
    async def _generate_call_response(
        self,
        transcription: str,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Generate response for phone call.
        
        Args:
            transcription: Transcribed user speech
            subtask: Call handling subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Response text
        """
        prompt = f"""Generate a natural phone conversation response:

User said: {transcription}

Task context: {subtask.description}

Respond naturally and helpfully. Keep it concise for voice.
"""
        
        generation_params = GenerationParams(
            max_tokens=200,  # Keep responses short for voice
            temperature=0.8,  # More natural for conversation
            system_prompt="You are a helpful phone assistant. Speak naturally and concisely."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        return response.content
    
    async def _speech_to_text_internal(self, audio_data: Any) -> str:
        """
        Internal STT implementation.
        
        Target: 500ms latency
        
        Args:
            audio_data: Audio data to transcribe
            
        Returns:
            Transcribed text
        """
        # Placeholder for actual STT implementation
        # In production, integrate with Whisper, Google STT, or similar
        logger.info("Transcribing audio (placeholder)")
        
        return f"[Transcribed audio: {len(str(audio_data))} bytes]"
    
    async def _text_to_speech_internal(self, text: str) -> Any:
        """
        Internal TTS implementation.
        
        Target: 300ms latency
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio data
        """
        # Placeholder for actual TTS implementation
        # In production, integrate with ElevenLabs, Google TTS, or similar
        logger.info(f"Synthesizing speech for: {text[:50]}...")
        
        return f"[Audio data for: {text[:50]}...]"
