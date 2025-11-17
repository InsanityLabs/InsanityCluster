"""
Project Manager Agent for CRUST layer.

Handles project management tasks including planning, tracking, progress reporting,
and risk identification.
"""
import logging
from datetime import datetime
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


class ProjectManagerAgent(BaseAgent):
    """
    Specialized agent for project management tasks.
    
    Capabilities:
    - Project planning and scheduling
    - Progress tracking and reporting
    - Risk identification and mitigation
    - Timeline feasibility validation
    - Resource allocation
    """
    
    def __init__(self, model_router: ModelRouter):
        """Initialize Project Manager Agent."""
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.COST_OPTIMIZED,
            max_cost=0.4,
            required_capabilities=[],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.PROJECT_MANAGER,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """Execute project management subtask."""
        logger.info(f"Project Manager agent executing: {subtask.description}")
        
        try:
            task_type = self._identify_task_type(subtask.description)
            model_strategy = self.select_model_strategy(subtask)
            
            if task_type == "planning":
                output = await self._create_project_plan(subtask, context, model_strategy)
            elif task_type == "tracking":
                output = await self._track_progress(subtask, context, model_strategy)
            elif task_type == "reporting":
                output = await self._generate_progress_report(subtask, context, model_strategy)
            elif task_type == "risk":
                output = await self._identify_risks(subtask, context, model_strategy)
            else:
                output = await self._execute_generic_pm_task(subtask, context, model_strategy)
            
            validation_score = self.validate_output(output, subtask)
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 900)
            model_used = context.get("last_model_used", "gpt-5-mini")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Project Manager agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """Select model strategy for PM tasks."""
        desc_lower = subtask.description.lower()
        
        # Complex planning requires better models
        if any(kw in desc_lower for kw in ["plan", "strategy", "architecture"]):
            return ModelStrategy(
                routing_mode=RoutingMode.TASK_SPECIFIC,
                max_cost=0.6,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        return self.default_model_strategy
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """Validate PM output with timeline feasibility check."""
        if not isinstance(output, (str, dict)):
            return 0.0
        
        output_str = str(output)
        checks_passed = 0
        total_checks = 5
        
        if output_str.strip() and len(output_str) > 50:
            checks_passed += 1
        if any(marker in output_str for marker in ["1.", "2.", "•", "-", "Phase", "Task"]):
            checks_passed += 1
        if any(term in output_str.lower() for term in ["timeline", "deadline", "milestone", "deliverable"]):
            checks_passed += 1
        if not any(err in output_str.lower() for err in ["error", "failed", "invalid"]):
            checks_passed += 1
        if any(pm_term in output_str.lower() for pm_term in ["project", "task", "resource", "risk"]):
            checks_passed += 1
        
        return checks_passed / total_checks
    
    def _identify_task_type(self, description: str) -> str:
        """Identify PM task type."""
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["plan", "schedule", "organize"]):
            return "planning"
        elif any(kw in desc_lower for kw in ["track", "monitor", "status"]):
            return "tracking"
        elif any(kw in desc_lower for kw in ["report", "progress", "update"]):
            return "reporting"
        elif any(kw in desc_lower for kw in ["risk", "issue", "blocker"]):
            return "risk"
        return "generic"
    
    async def _create_project_plan(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Create project plan."""
        project_name = context.get("project_name", "Project")
        duration = context.get("duration", "3 months")
        team_size = context.get("team_size", 5)
        
        prompt = f"""Create comprehensive project plan:

Project: {project_name}
Duration: {duration}
Team Size: {team_size}
Task: {subtask.description}

Include:
1. Project phases and milestones
2. Task breakdown
3. Timeline and dependencies
4. Resource allocation
5. Success criteria
6. Risk considerations
"""
        
        generation_params = GenerationParams(
            max_tokens=2500,
            temperature=0.4,
            system_prompt="You are an experienced project manager. Create realistic, actionable plans."
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
        
        return {
            "type": "project_plan",
            "project_name": project_name,
            "plan": response.content,
            "duration": duration,
            "feasibility": self._assess_timeline_feasibility(response.content, duration),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _track_progress(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Track project progress."""
        completed_tasks = context.get("completed_tasks", [])
        pending_tasks = context.get("pending_tasks", [])
        
        prompt = f"""Track project progress:

Task: {subtask.description}
Completed: {len(completed_tasks)} tasks
Pending: {len(pending_tasks)} tasks

Provide:
1. Progress summary
2. Completion percentage
3. On-track status
4. Blockers or issues
5. Next steps
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.3,
            system_prompt="You are a project tracker. Provide clear status updates."
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
        
        completion_rate = len(completed_tasks) / (len(completed_tasks) + len(pending_tasks)) if (completed_tasks or pending_tasks) else 0.0
        
        return {
            "type": "progress_tracking",
            "tracking": response.content,
            "completion_rate": completion_rate,
            "completed_count": len(completed_tasks),
            "pending_count": len(pending_tasks),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_progress_report(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Generate progress report."""
        report_period = context.get("report_period", "weekly")
        
        prompt = f"""Generate {report_period} progress report:

Task: {subtask.description}

Include:
1. Executive summary
2. Accomplishments
3. Current status
4. Upcoming milestones
5. Issues and risks
6. Action items
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are a project reporter. Create clear, professional reports."
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
        
        return {
            "type": "progress_report",
            "period": report_period,
            "report": response.content,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _identify_risks(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Identify and assess project risks."""
        project_context = context.get("project_context", "")
        
        prompt = f"""Identify project risks:

Task: {subtask.description}
Context: {project_context}

Provide:
1. Identified risks
2. Risk severity (high/medium/low)
3. Impact assessment
4. Mitigation strategies
5. Contingency plans
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.4,
            system_prompt="You are a risk management expert. Identify and assess risks thoroughly."
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
        
        return {
            "type": "risk_assessment",
            "assessment": response.content,
            "risk_level": self._assess_overall_risk(response.content),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_generic_pm_task(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Execute generic PM task."""
        prompt = f"""Complete project management task:

Task: {subtask.description}

Provide professional project management guidance.
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.4,
            system_prompt="You are a project manager. Provide practical, actionable guidance."
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
    
    def _assess_timeline_feasibility(self, plan: str, duration: str) -> str:
        """Assess timeline feasibility."""
        plan_lower = plan.lower()
        
        # Simple heuristic based on complexity indicators
        complexity_indicators = ["complex", "challenging", "extensive", "multiple phases"]
        complexity_count = sum(1 for indicator in complexity_indicators if indicator in plan_lower)
        
        if complexity_count >= 3:
            return "challenging"
        elif complexity_count >= 1:
            return "feasible"
        else:
            return "achievable"
    
    def _assess_overall_risk(self, assessment: str) -> str:
        """Assess overall risk level."""
        assessment_lower = assessment.lower()
        
        high_risk_count = assessment_lower.count("high risk") + assessment_lower.count("critical")
        medium_risk_count = assessment_lower.count("medium risk") + assessment_lower.count("moderate")
        
        if high_risk_count >= 2:
            return "high"
        elif high_risk_count >= 1 or medium_risk_count >= 3:
            return "medium"
        else:
            return "low"
