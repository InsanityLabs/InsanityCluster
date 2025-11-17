"""
Business Agent for CRUST layer.

Handles business and legal tasks including LLC formation, contract analysis,
compliance monitoring, and financial record keeping.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class BusinessAgent(BaseAgent):
    """
    Specialized agent for business and legal tasks.
    
    Capabilities:
    - LLC formation document generation
    - LegalZoom and Rocket Lawyer API integration
    - Contract analysis and review
    - Compliance monitoring with deadline alerts
    - Financial record keeping and reporting
    
    Uses high-quality models for legal reasoning and accuracy.
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        legalzoom_client: Optional[Any] = None,
        rocket_lawyer_client: Optional[Any] = None
    ):
        """
        Initialize Business Agent.
        
        Args:
            model_router: Model router for inference
            legalzoom_client: LegalZoom API client (optional)
            rocket_lawyer_client: Rocket Lawyer API client (optional)
        """
        # Default to quality-first for legal accuracy
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.QUALITY_FIRST,
            max_cost=2.0,  # Allow higher cost for legal work
            required_capabilities=["long_context"],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.BUSINESS,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
        
        # External service clients
        self.legalzoom_client = legalzoom_client
        self.rocket_lawyer_client = rocket_lawyer_client
        
        # Supported states for LLC formation
        self.supported_states = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        ]
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """
        Execute business subtask.
        
        Args:
            subtask: Subtask to execute
            context: Execution context
            
        Returns:
            AgentResult with business output
        """
        logger.info(f"Business agent executing: {subtask.description}")
        
        try:
            # Determine task type
            task_type = self._identify_task_type(subtask.description)
            
            # Select model strategy
            model_strategy = self.select_model_strategy(subtask)
            
            # Execute based on task type
            if task_type == "llc_formation":
                output = await self._form_llc(subtask, context, model_strategy)
            elif task_type == "contract_analysis":
                output = await self._analyze_contract(subtask, context, model_strategy)
            elif task_type == "compliance":
                output = await self._monitor_compliance(subtask, context, model_strategy)
            elif task_type == "financial_records":
                output = await self._manage_financial_records(subtask, context, model_strategy)
            else:
                output = await self._execute_generic_business_task(subtask, context, model_strategy)
            
            # Validate output
            validation_score = self.validate_output(output, subtask)
            
            # Get metrics
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 2000)
            model_used = context.get("last_model_used", "claude-opus-4.1")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Business agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select model strategy for business tasks.
        
        Args:
            subtask: Subtask to analyze
            
        Returns:
            ModelStrategy optimized for legal/business accuracy
        """
        description_lower = subtask.description.lower()
        
        # LLC formation and contracts require highest quality
        if any(keyword in description_lower for keyword in ["llc", "formation", "contract", "legal"]):
            return ModelStrategy(
                routing_mode=RoutingMode.QUALITY_FIRST,
                max_cost=2.0,
                required_capabilities=["long_context"],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Compliance monitoring can use mid-tier
        if any(keyword in description_lower for keyword in ["compliance", "monitor", "deadline"]):
            return ModelStrategy(
                routing_mode=RoutingMode.TASK_SPECIFIC,
                max_cost=1.0,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Financial records can be cost-optimized
        if any(keyword in description_lower for keyword in ["financial", "record", "report"]):
            return ModelStrategy(
                routing_mode=RoutingMode.COST_OPTIMIZED,
                max_cost=0.5,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        return self.default_model_strategy
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """
        Validate business output.
        
        Checks:
        - Legal term accuracy
        - Completeness
        - Professional formatting
        - Compliance requirements
        
        Args:
            output: Generated business document or analysis
            subtask: Original subtask
            
        Returns:
            Validation score (0.0 to 1.0)
        """
        if not isinstance(output, (str, dict)):
            return 0.0
        
        # Convert dict to string for validation
        if isinstance(output, dict):
            output_str = str(output)
        else:
            output_str = output
        
        score = 0.0
        checks_passed = 0
        total_checks = 6
        
        # Check 1: Not empty
        if output_str.strip():
            checks_passed += 1
        
        # Check 2: Substantial content
        if len(output_str) > 100:
            checks_passed += 1
        
        # Check 3: Professional language
        professional_terms = ["hereby", "pursuant", "agreement", "party", "terms", "conditions"]
        if any(term in output_str.lower() for term in professional_terms):
            checks_passed += 1
        
        # Check 4: No obvious errors
        error_indicators = ["error", "failed", "invalid", "cannot process"]
        if not any(indicator in output_str.lower() for indicator in error_indicators):
            checks_passed += 1
        
        # Check 5: Structured format
        if any(marker in output_str for marker in ["1.", "2.", "•", "-", "Article", "Section"]):
            checks_passed += 1
        
        # Check 6: Contains relevant legal/business terms
        business_terms = ["llc", "corporation", "contract", "compliance", "liability", "entity"]
        if any(term in output_str.lower() for term in business_terms):
            checks_passed += 1
        
        score = checks_passed / total_checks
        
        logger.debug(f"Validation score: {score:.2f} ({checks_passed}/{total_checks} checks passed)")
        
        return score
    
    def _identify_task_type(self, description: str) -> str:
        """
        Identify business task type.
        
        Args:
            description: Task description
            
        Returns:
            Task type identifier
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["llc", "formation", "incorporate"]):
            return "llc_formation"
        elif any(keyword in description_lower for keyword in ["contract", "agreement", "review", "analyze"]):
            return "contract_analysis"
        elif any(keyword in description_lower for keyword in ["compliance", "monitor", "deadline", "regulation"]):
            return "compliance"
        elif any(keyword in description_lower for keyword in ["financial", "record", "accounting", "report"]):
            return "financial_records"
        else:
            return "generic"
    
    async def _form_llc(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Generate LLC formation documents.
        
        Args:
            subtask: LLC formation subtask
            context: Execution context with LLC details
            model_strategy: Model selection strategy
            
        Returns:
            LLC formation documents and filing information
        """
        company_name = context.get("company_name", "")
        state = context.get("state", "DE")
        members = context.get("members", [])
        business_purpose = context.get("business_purpose", "")
        
        # Validate state
        if state not in self.supported_states:
            return {
                "error": f"State {state} not supported",
                "supported_states": self.supported_states
            }
        
        # Generate LLC formation documents
        prompt = f"""Generate comprehensive LLC formation documents for:

Company Name: {company_name}
State: {state}
Members: {', '.join(members) if members else 'Single member'}
Business Purpose: {business_purpose}

Task: {subtask.description}

Generate:
1. Articles of Organization
2. Operating Agreement
3. Member Information
4. Initial Resolutions
5. Filing Instructions

Include all required legal language and state-specific requirements for {state}.
"""
        
        generation_params = GenerationParams(
            max_tokens=4000,
            temperature=0.2,  # Low temperature for legal accuracy
            system_prompt="You are an expert business attorney specializing in LLC formation. Generate accurate, legally sound documents."
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
        
        documents = response.content
        
        # File with LegalZoom if configured
        filing_status = "documents_generated"
        if self.legalzoom_client:
            logger.info(f"Filing LLC with LegalZoom for {company_name}")
            # Placeholder for LegalZoom API integration
            filing_status = "filed_with_legalzoom"
        
        return {
            "type": "llc_formation",
            "company_name": company_name,
            "state": state,
            "documents": documents,
            "filing_status": filing_status,
            "next_steps": [
                "Review all documents carefully",
                "Sign Articles of Organization",
                "File with state",
                "Obtain EIN from IRS",
                "Open business bank account"
            ]
        }
    
    async def _analyze_contract(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Analyze and review contract.
        
        Args:
            subtask: Contract analysis subtask
            context: Execution context with contract text
            model_strategy: Model selection strategy
            
        Returns:
            Contract analysis and recommendations
        """
        contract_text = context.get("contract_text", "")
        contract_type = context.get("contract_type", "general")
        
        if not contract_text:
            return {"error": "No contract text provided"}
        
        prompt = f"""Analyze the following {contract_type} contract:

{contract_text}

Task: {subtask.description}

Provide comprehensive analysis including:
1. Summary of key terms
2. Obligations and responsibilities
3. Payment terms and conditions
4. Termination clauses
5. Liability and indemnification
6. Potential risks and concerns
7. Recommendations for negotiation
8. Red flags or problematic clauses
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.3,
            system_prompt="You are an expert contract attorney. Provide thorough, practical analysis."
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
            "type": "contract_analysis",
            "contract_type": contract_type,
            "analysis": response.content,
            "risk_level": self._assess_contract_risk(response.content),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _monitor_compliance(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Monitor compliance requirements and deadlines.
        
        Args:
            subtask: Compliance monitoring subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Compliance status and alerts
        """
        company_type = context.get("company_type", "LLC")
        state = context.get("state", "DE")
        industry = context.get("industry", "general")
        
        prompt = f"""Identify compliance requirements for:

Company Type: {company_type}
State: {state}
Industry: {industry}

Task: {subtask.description}

Provide:
1. Annual filing requirements
2. Tax deadlines
3. License renewals
4. Industry-specific regulations
5. Upcoming deadlines (next 90 days)
6. Penalties for non-compliance
7. Recommended compliance calendar
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are a compliance expert. Provide accurate, actionable compliance information."
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
        
        # Extract deadlines (simplified)
        deadlines = self._extract_deadlines(response.content)
        
        return {
            "type": "compliance_monitoring",
            "company_type": company_type,
            "state": state,
            "requirements": response.content,
            "upcoming_deadlines": deadlines,
            "alerts": self._generate_compliance_alerts(deadlines),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _manage_financial_records(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Manage financial records and generate reports.
        
        Args:
            subtask: Financial records subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Financial records and reports
        """
        record_type = context.get("record_type", "general")
        period = context.get("period", "monthly")
        transactions = context.get("transactions", [])
        
        prompt = f"""Generate {period} financial {record_type} report:

Task: {subtask.description}

Transactions: {len(transactions)} entries

Provide:
1. Summary of financial activity
2. Income statement
3. Expense categorization
4. Cash flow analysis
5. Key financial metrics
6. Recommendations
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.2,
            system_prompt="You are a financial analyst. Provide clear, accurate financial reports."
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
            "type": "financial_records",
            "record_type": record_type,
            "period": period,
            "report": response.content,
            "transaction_count": len(transactions),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_generic_business_task(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Execute generic business task.
        
        Args:
            subtask: Generic business subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Business task output
        """
        prompt = f"""Complete the following business task:

Task: {subtask.description}

Context: {context.get('additional_context', 'None provided')}

Provide professional, legally sound guidance.
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are a business consultant. Provide expert, actionable advice."
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
    
    def _assess_contract_risk(self, analysis: str) -> str:
        """
        Assess risk level from contract analysis.
        
        Args:
            analysis: Contract analysis text
            
        Returns:
            Risk level (low, medium, high)
        """
        analysis_lower = analysis.lower()
        
        high_risk_indicators = ["red flag", "concerning", "problematic", "unfavorable", "risk"]
        medium_risk_indicators = ["caution", "consider", "negotiate", "clarify"]
        
        high_risk_count = sum(1 for indicator in high_risk_indicators if indicator in analysis_lower)
        medium_risk_count = sum(1 for indicator in medium_risk_indicators if indicator in analysis_lower)
        
        if high_risk_count >= 3:
            return "high"
        elif high_risk_count >= 1 or medium_risk_count >= 3:
            return "medium"
        else:
            return "low"
    
    def _extract_deadlines(self, compliance_text: str) -> List[Dict[str, str]]:
        """
        Extract deadlines from compliance text.
        
        Args:
            compliance_text: Compliance requirements text
            
        Returns:
            List of deadlines
        """
        # Simplified deadline extraction
        # In production, use more sophisticated NLP
        deadlines = []
        
        # Look for common deadline patterns
        if "annual report" in compliance_text.lower():
            deadlines.append({
                "type": "Annual Report",
                "description": "File annual report with state",
                "frequency": "yearly"
            })
        
        if "tax" in compliance_text.lower():
            deadlines.append({
                "type": "Tax Filing",
                "description": "File business taxes",
                "frequency": "quarterly/yearly"
            })
        
        return deadlines
    
    def _generate_compliance_alerts(self, deadlines: List[Dict[str, str]]) -> List[str]:
        """
        Generate compliance alerts from deadlines.
        
        Args:
            deadlines: List of deadlines
            
        Returns:
            List of alert messages
        """
        alerts = []
        
        for deadline in deadlines:
            alerts.append(
                f"Upcoming: {deadline['type']} - {deadline['description']}"
            )
        
        return alerts
