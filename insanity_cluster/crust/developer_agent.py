"""
Developer Agent for CRUST layer.

Handles software development tasks including code generation, review,
debugging, CI/CD setup, and documentation.
"""
import logging
import re
from typing import Any, Dict, List, Optional

from insanity_cluster.common.models import (
    AgentResult,
    AgentType,
    ModelStrategy,
    PrivacyLevel,
    RoutingMode,
    Subtask,
)
from insanity_cluster.crust.base_agent import (
    AgentExecutionError,
    BaseAgent,
    ValidationError,
)
from insanity_cluster.pan.model_router import ModelRouter
from insanity_cluster.pan.models import GenerationParams

logger = logging.getLogger(__name__)


class DeveloperAgent(BaseAgent):
    """
    Specialized agent for software development tasks.
    
    Capabilities:
    - Code generation in multiple languages
    - Code review and refactoring suggestions
    - Debugging with error analysis
    - CI/CD pipeline setup
    - Documentation generation
    - Syntax checking and linting
    """
    
    def __init__(self, model_router: ModelRouter):
        """
        Initialize Developer Agent.
        
        Args:
            model_router: Model router for inference
        """
        # Default to quality-first for code generation
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.QUALITY_FIRST,
            max_cost=1.0,  # Allow up to $1 per task
            required_capabilities=["long_context"],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.DEVELOPER,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
        
        # Supported programming languages
        self.supported_languages = [
            "python", "javascript", "typescript", "java", "go",
            "rust", "c", "cpp", "csharp", "ruby", "php", "swift",
            "kotlin", "scala", "sql", "bash", "powershell"
        ]
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """
        Execute development subtask.
        
        Args:
            subtask: Subtask to execute
            context: Execution context
            
        Returns:
            AgentResult with code or analysis
        """
        logger.info(f"Developer agent executing: {subtask.description}")
        
        try:
            # Determine task type from description
            task_type = self._identify_task_type(subtask.description)
            
            # Select appropriate model strategy
            model_strategy = self.select_model_strategy(subtask)
            
            # Execute based on task type
            if task_type == "code_generation":
                output = await self._generate_code(subtask, context, model_strategy)
            elif task_type == "code_review":
                output = await self._review_code(subtask, context, model_strategy)
            elif task_type == "debugging":
                output = await self._debug_code(subtask, context, model_strategy)
            elif task_type == "cicd_setup":
                output = await self._setup_cicd(subtask, context, model_strategy)
            elif task_type == "documentation":
                output = await self._generate_documentation(subtask, context, model_strategy)
            else:
                # Generic development task
                output = await self._execute_generic_task(subtask, context, model_strategy)
            
            # Validate output
            validation_score = self.validate_output(output, subtask)
            
            # Calculate metrics (from context or model response)
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 1000)
            model_used = context.get("last_model_used", "claude-sonnet-4.5")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Developer agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select model strategy based on task complexity.
        
        Args:
            subtask: Subtask to analyze
            
        Returns:
            ModelStrategy optimized for development tasks
        """
        description_lower = subtask.description.lower()
        
        # Use specialized code model for code generation
        if any(keyword in description_lower for keyword in ["generate", "write", "create", "implement"]):
            return ModelStrategy(
                routing_mode=RoutingMode.TASK_SPECIFIC,
                max_cost=1.0,
                required_capabilities=["long_context"],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Use quality-first for complex tasks
        if any(keyword in description_lower for keyword in ["refactor", "optimize", "architect"]):
            return ModelStrategy(
                routing_mode=RoutingMode.QUALITY_FIRST,
                max_cost=1.0,
                required_capabilities=["long_context"],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Use cost-optimized for simple tasks
        if any(keyword in description_lower for keyword in ["fix", "debug", "review"]):
            return ModelStrategy(
                routing_mode=RoutingMode.COST_OPTIMIZED,
                max_cost=0.5,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Default strategy
        return self.default_model_strategy
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """
        Validate code output.
        
        Checks:
        - Syntax validity (basic check)
        - Code structure
        - Presence of required elements
        
        Args:
            output: Generated code or analysis
            subtask: Original subtask
            
        Returns:
            Validation score (0.0 to 1.0)
        """
        if not isinstance(output, str):
            return 0.0
        
        score = 0.0
        checks_passed = 0
        total_checks = 5
        
        # Check 1: Output is not empty
        if output.strip():
            checks_passed += 1
        
        # Check 2: Contains code blocks or structured content
        if "```" in output or any(keyword in output for keyword in ["def ", "function ", "class ", "import "]):
            checks_passed += 1
        
        # Check 3: No obvious error messages
        error_indicators = ["error:", "exception:", "failed:", "cannot", "unable"]
        if not any(indicator in output.lower() for indicator in error_indicators):
            checks_passed += 1
        
        # Check 4: Reasonable length (not too short)
        if len(output) > 50:
            checks_passed += 1
        
        # Check 5: Contains relevant keywords from subtask
        task_keywords = self._extract_keywords(subtask.description)
        if any(keyword.lower() in output.lower() for keyword in task_keywords):
            checks_passed += 1
        
        score = checks_passed / total_checks
        
        logger.debug(f"Validation score: {score:.2f} ({checks_passed}/{total_checks} checks passed)")
        
        return score
    
    def _identify_task_type(self, description: str) -> str:
        """
        Identify the type of development task.
        
        Args:
            description: Task description
            
        Returns:
            Task type identifier
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["generate", "write", "create", "implement"]):
            return "code_generation"
        elif any(keyword in description_lower for keyword in ["review", "analyze", "refactor"]):
            return "code_review"
        elif any(keyword in description_lower for keyword in ["debug", "fix", "error", "bug"]):
            return "debugging"
        elif any(keyword in description_lower for keyword in ["ci/cd", "pipeline", "deploy", "github actions"]):
            return "cicd_setup"
        elif any(keyword in description_lower for keyword in ["document", "readme", "docs", "comment"]):
            return "documentation"
        else:
            return "generic"
    
    async def _generate_code(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Generate code based on specifications.
        
        Args:
            subtask: Code generation subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Generated code
        """
        # Build prompt for code generation
        prompt = self._build_code_generation_prompt(subtask, context)
        
        # Generate with model
        generation_params = GenerationParams(
            max_tokens=4000,
            temperature=0.2,  # Lower temperature for more deterministic code
            system_prompt="You are an expert software developer. Generate clean, well-documented, production-ready code."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        # Store metrics in context for result creation
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return response.content
    
    async def _review_code(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Review code and provide suggestions.
        
        Args:
            subtask: Code review subtask
            context: Execution context with code to review
            model_strategy: Model selection strategy
            
        Returns:
            Review feedback and suggestions
        """
        code_to_review = context.get("code", "")
        
        prompt = f"""Review the following code and provide detailed feedback:

{code_to_review}

Task: {subtask.description}

Provide:
1. Overall assessment
2. Potential bugs or issues
3. Performance improvements
4. Code quality suggestions
5. Security considerations
6. Refactoring recommendations
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are an expert code reviewer. Provide constructive, actionable feedback."
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
    
    async def _debug_code(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Debug code and analyze errors.
        
        Args:
            subtask: Debugging subtask
            context: Execution context with error information
            model_strategy: Model selection strategy
            
        Returns:
            Debugging analysis and fixes
        """
        code = context.get("code", "")
        error_message = context.get("error_message", "")
        stack_trace = context.get("stack_trace", "")
        
        prompt = f"""Debug the following code issue:

Code:
{code}

Error Message:
{error_message}

Stack Trace:
{stack_trace}

Task: {subtask.description}

Provide:
1. Root cause analysis
2. Explanation of the error
3. Fixed code
4. Prevention strategies
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.2,
            system_prompt="You are an expert debugger. Analyze errors systematically and provide clear fixes."
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
    
    async def _setup_cicd(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Set up CI/CD pipeline configuration.
        
        Args:
            subtask: CI/CD setup subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            CI/CD configuration files
        """
        platform = context.get("cicd_platform", "github_actions")
        project_type = context.get("project_type", "python")
        
        prompt = f"""Create a CI/CD pipeline configuration for:

Platform: {platform}
Project Type: {project_type}
Task: {subtask.description}

Include:
1. Build steps
2. Test execution
3. Linting and code quality checks
4. Deployment configuration
5. Environment variables setup
6. Best practices and comments
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.2,
            system_prompt="You are a DevOps expert. Create production-ready CI/CD configurations."
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
    
    async def _generate_documentation(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Generate technical documentation.
        
        Args:
            subtask: Documentation subtask
            context: Execution context with code
            model_strategy: Model selection strategy
            
        Returns:
            Generated documentation
        """
        code = context.get("code", "")
        doc_type = context.get("doc_type", "readme")
        
        prompt = f"""Generate {doc_type} documentation for:

Code:
{code}

Task: {subtask.description}

Include:
1. Overview and purpose
2. Installation instructions
3. Usage examples
4. API reference (if applicable)
5. Configuration options
6. Contributing guidelines (if README)
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.4,
            system_prompt="You are a technical writer. Create clear, comprehensive documentation."
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
    
    async def _execute_generic_task(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Execute generic development task.
        
        Args:
            subtask: Generic subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Task output
        """
        prompt = f"""Complete the following development task:

Task: {subtask.description}

Context: {context.get('additional_context', 'None provided')}

Provide a complete, production-ready solution.
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.3,
            system_prompt="You are an expert software developer. Provide high-quality solutions."
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
    
    def _build_code_generation_prompt(
        self,
        subtask: Subtask,
        context: Dict[str, Any]
    ) -> str:
        """
        Build detailed prompt for code generation.
        
        Args:
            subtask: Code generation subtask
            context: Execution context
            
        Returns:
            Formatted prompt
        """
        language = context.get("language", "python")
        requirements = context.get("requirements", [])
        existing_code = context.get("existing_code", "")
        
        prompt = f"""Generate {language} code for the following task:

Task: {subtask.description}

Requirements:
"""
        
        if requirements:
            for i, req in enumerate(requirements, 1):
                prompt += f"{i}. {req}\n"
        else:
            prompt += "- Follow best practices\n- Include error handling\n- Add docstrings/comments\n"
        
        if existing_code:
            prompt += f"\nExisting Code Context:\n{existing_code}\n"
        
        prompt += "\nProvide complete, working code with comments."
        
        return prompt
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        return keywords[:10]  # Return top 10 keywords
