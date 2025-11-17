"""
Creative Agent for CRUST layer.

Handles creative tasks including copywriting, design, content creation,
and brand consistency validation.
"""
import logging
from typing import Any, Dict

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


class CreativeAgent(BaseAgent):
    """
    Specialized agent for creative tasks.
    
    Capabilities:
    - Copywriting and content creation
    - Design concepts (with vision models)
    - Brand consistency validation
    - Marketing materials
    - Creative ideation
    """
    
    def __init__(self, model_router: ModelRouter):
        """Initialize Creative Agent."""
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.QUALITY_FIRST,
            max_cost=0.8,
            required_capabilities=[],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.CREATIVE,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """Execute creative subtask."""
        logger.info(f"Creative agent executing: {subtask.description}")
        
        try:
            task_type = self._identify_task_type(subtask.description)
            model_strategy = self.select_model_strategy(subtask)
            
            if task_type == "copywriting":
                output = await self._create_copy(subtask, context, model_strategy)
            elif task_type == "design":
                output = await self._create_design_concept(subtask, context, model_strategy)
            elif task_type == "content":
                output = await self._create_content(subtask, context, model_strategy)
            else:
                output = await self._execute_generic_creative(subtask, context, model_strategy)
            
            validation_score = self.validate_output(output, subtask)
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 1000)
            model_used = context.get("last_model_used", "gpt-5.1")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Creative agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """Select model strategy for creative tasks."""
        return ModelStrategy(
            routing_mode=RoutingMode.QUALITY_FIRST,
            max_cost=0.8,
            required_capabilities=["vision"] if "design" in subtask.description.lower() else [],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """Validate creative output."""
        if not isinstance(output, str):
            return 0.0
        
        checks_passed = 0
        total_checks = 4
        
        if output.strip() and len(output) > 50:
            checks_passed += 1
        if not any(err in output.lower() for err in ["error", "failed", "cannot"]):
            checks_passed += 1
        if any(creative in output.lower() for creative in ["creative", "engaging", "compelling"]):
            checks_passed += 1
        if len(output.split()) > 20:
            checks_passed += 1
        
        return checks_passed / total_checks
    
    def _identify_task_type(self, description: str) -> str:
        """Identify creative task type."""
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["copy", "write", "text"]):
            return "copywriting"
        elif any(kw in desc_lower for kw in ["design", "visual", "graphic"]):
            return "design"
        elif any(kw in desc_lower for kw in ["content", "article", "post"]):
            return "content"
        return "generic"
    
    async def _create_copy(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Create copywriting content."""
        tone = context.get("tone", "professional")
        target_audience = context.get("target_audience", "general")
        
        prompt = f"""Create compelling copy for:

Task: {subtask.description}
Tone: {tone}
Target Audience: {target_audience}

Create engaging, persuasive copy that captures attention and drives action.
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.8,
            system_prompt="You are a creative copywriter. Write compelling, engaging copy."
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
    
    async def _create_design_concept(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Create design concept."""
        style = context.get("style", "modern")
        colors = context.get("colors", "brand colors")
        
        prompt = f"""Create a design concept for:

Task: {subtask.description}
Style: {style}
Colors: {colors}

Describe the visual design in detail including layout, typography, imagery, and overall aesthetic.
"""
        
        generation_params = GenerationParams(
            max_tokens=1000,
            temperature=0.7,
            system_prompt="You are a creative designer. Describe compelling visual concepts."
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
    
    async def _create_content(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Create content."""
        content_type = context.get("content_type", "article")
        
        prompt = f"""Create {content_type} content for:

Task: {subtask.description}

Create engaging, high-quality content that informs and entertains.
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.7,
            system_prompt="You are a content creator. Write engaging, valuable content."
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
    
    async def _execute_generic_creative(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Execute generic creative task."""
        prompt = f"""Complete this creative task:

Task: {subtask.description}

Be creative, original, and engaging.
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.8,
            system_prompt="You are a creative professional. Deliver original, engaging work."
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
